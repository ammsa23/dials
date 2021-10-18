#!/usr/bin/env python
#
# dials.potato.py
#
#  Copyright (C) 2018 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import absolute_import, division

import json
import logging
from collections import OrderedDict
from math import pi

from jinja2 import ChoiceLoader, Environment, PackageLoader

from libtbx.phil import parse
from scitbx import matrix

from dials.algorithms.profile_model.gaussian_rs import BBoxCalculator, MaskCalculator
from dials.algorithms.profile_model.gaussian_rs.calculator import (
    ComputeEsdBeamDivergence,
)
from dials.algorithms.profile_model.potato import chisq_pdf
from dials.algorithms.profile_model.potato.indexer import reindex
from dials.algorithms.profile_model.potato.model import ProfileModelFactory
from dials.algorithms.profile_model.potato.parameterisation import ModelState
from dials.algorithms.profile_model.potato.plots import (
    plot_distance_from_ewald_sphere,
    plot_partiality,
)
from dials.algorithms.profile_model.potato.refiner import Refiner as ProfileRefiner
from dials.algorithms.profile_model.potato.refiner import RefinerData
from dials.algorithms.refinement.corrgram import corrgram
from dials.algorithms.spot_prediction import IndexGenerator
from dials.array_family import flex

logger = logging.getLogger("dials." + __name__)

# Parameters
phil_scope = parse(
    """

  profile
  {

    rlp_mosaicity {

      model = simple1 simple6 *angular2 angular4 angular6
        .type = choice

    }

    wavelength_spread {

      model = *delta gaussian
        .type = choice

    }

    unit_cell {

      fixed = False
        .type = bool

    }

    orientation {

      fixed = False
        .type = bool

    }

  }

  indexing {

    fail_on_bad_index = False
      .type = bool

  }

  refinement {

    max_separation = 2
      .type = float

    outlier_probability = 0.975
      .type = float

    n_macro_cycles = 3
      .type = int

    n_cycles = 3
      .type = int

    min_n_reflections=10
      .type = int

  }

  prediction {
    d_min = None
      .type = float

    probability = 0.9973
      .type = float
  }

  integration {

    use_crude_shoebox_mask = False
      .type = bool

    shoebox {

      probability = 0.9973
        .type = float

    }

    corrections {
      lp = True
        .type = bool
      dqe = True
        .type = bool
      partiality = True
        .type = bool
    }

  }

  debug {
    output {

      strong_spots = False
        .type = bool

      shoeboxes = True
        .type = bool

      profile_model = True
        .type = bool

      history = True
        .type = bool

      plots = False
        .type = bool

      print_shoeboxes = False
        .type = bool
    }
  }


"""
)


def _compute_beam_vector(experiment, reflection_table):
    """Compute the obseved beam vector"""
    s1_obs = flex.vec3_double(len(reflection_table))
    for i in range(len(s1_obs)):
        x, y, _ = reflection_table["xyzobs.px.value"][i]
        s1_obs[i] = experiment.detector[0].get_pixel_lab_coord((x, y))
    return s1_obs


def _compute_bbox(experiment, reflection_table, sigma_d, s1="s1_obs"):
    """Compute the bounding box"""

    # Initialise the bounding box calculator
    compute_bbox = BBoxCalculator(
        experiment.crystal,
        experiment.beam,
        experiment.detector,
        experiment.goniometer,
        experiment.scan,
        sigma_d * 6,
        0,
    )

    # Compute the bounding box
    bbox = compute_bbox(
        reflection_table[s1],
        reflection_table["xyzcal.px"].parts()[2],
        reflection_table["panel"],
    )

    return bbox


def _compute_mask(
    experiment, reflection_table, sigma_d, s1="s1_obs", strong_shoeboxes=None
):
    """Compute the spot mask"""

    # Initialise the mask calculator
    mask_foreground = MaskCalculator(
        experiment.crystal,
        experiment.beam,
        experiment.detector,
        experiment.goniometer,
        experiment.scan,
        sigma_d * 3,
        0,
    )

    # Compute the reflection mask
    mask_foreground(
        reflection_table["shoebox"],
        reflection_table[s1],
        reflection_table["xyzcal.px"].parts()[2],
        reflection_table["panel"],
    )

    # if strong_shoeboxes given, apply the mask from this
    if strong_shoeboxes:
        # Apply strong spot mask
        assert len(reflection_table) == len(strong_shoeboxes)
        new_shoeboxes = reflection_table["shoebox"]
        for s in range(len(new_shoeboxes)):
            bbox_old = strong_shoeboxes[s].bbox
            mask_old = strong_shoeboxes[s].mask
            bbox_new = new_shoeboxes[s].bbox
            mask_new = new_shoeboxes[s].mask
            for j in range(mask_old.all()[1]):
                for i in range(mask_old.all()[2]):
                    ii = bbox_old[0] + i - bbox_new[0]
                    jj = bbox_old[2] + j - bbox_new[2]
                    if mask_old[0, j, i] == 5:
                        if (
                            ii >= 0
                            and jj >= 0
                            and jj < mask_new.all()[1]
                            and ii < mask_new.all()[2]
                        ):
                            assert mask_new[0, jj, ii] & (1 << 0)
                            mask_new[0, jj, ii] |= (1 << 2) | (1 << 3)


def initial_integrator(experiments, reflection_table):
    """Performs an initial integration of strong spots"""

    # some functions require an experimentlist, others just the experiment
    experiment = experiments[0]
    sel = reflection_table.get_flags(reflection_table.flags.strong)
    strong_refls = reflection_table.select(sel)
    strong_shoeboxes = strong_refls["shoebox"]  # Save the strong shoeboxes

    # Compute and initial spot size estimate and beam vector
    sigma_d = ComputeEsdBeamDivergence(experiment.detector, strong_refls).sigma()
    sigma_degrees = sigma_d * 180 / pi
    logger.info(
        f"Initial sigma d estimate for {len(strong_refls)} reflections\n"
        + f"Sigma D: {sigma_degrees:.5f} degrees\n",
    )
    strong_refls["s1_obs"] = _compute_beam_vector(experiment, strong_refls)
    strong_refls["bbox"] = _compute_bbox(experiment, strong_refls, sigma_d, "s1_obs")

    # allocate and extract shoebox
    strong_refls["shoebox"] = flex.shoebox(
        strong_refls["panel"], strong_refls["bbox"], allocate=True
    )
    strong_refls.extract_shoeboxes(experiment.imageset)

    _compute_mask(experiment, strong_refls, sigma_d, "s1_obs", strong_shoeboxes)

    logger.info(
        f"Computing background, intensity and centroids for {len(strong_refls)} reflections"
    )
    strong_refls.compute_background(experiments)
    strong_refls.compute_summed_intensity()

    n_sum = strong_refls.get_flags(strong_refls.flags.integrated_sum).count(True)
    logger.info(f"{n_sum} reflections integrated")

    strong_refls.compute_centroid(experiments)
    strong_refls.compute_d(experiments)

    return strong_refls, sigma_d


def final_integrator(
    experiments,
    reflection_table,
    sigma_d,
    use_crude_shoebox_mask=False,
    shoebox_probability=0.9973,
):
    """Performs an initial integration of all predicted spots"""

    experiment = experiments[0]
    logger.info("\n" + "=" * 80 + "\nIntegrating reflections")

    # first compute the bbox
    if use_crude_shoebox_mask:
        reflection_table["bbox"] = _compute_bbox(
            experiment, reflection_table, sigma_d, "s1"
        )
    else:
        # compute bbox from model
        profile = experiment.crystal.mosaicity
        profile.compute_bbox(experiments, reflection_table, shoebox_probability)

    # Select reflections within detector
    x0, x1, y0, y1, _, _ = reflection_table["bbox"].parts()
    xsize, ysize = experiment.detector[0].get_image_size()
    selection = (x1 > 0) & (y1 > 0) & (x0 < xsize) & (y0 < ysize)
    reflection_table = reflection_table.select(selection)

    reflection_table["shoebox"] = flex.shoebox(
        reflection_table["panel"], reflection_table["bbox"], allocate=True
    )
    reflection_table.extract_shoeboxes(experiment.imageset)

    if use_crude_shoebox_mask:
        _compute_mask(experiment, reflection_table, sigma_d, "s1")
    else:
        # compute the mask from the model.
        profile = experiment.crystal.mosaicity
        profile.compute_mask(experiments, reflection_table, shoebox_probability)

    logger.info(
        f"Computing background, intensity, corrections for {len(reflection_table)} reflections"
    )
    reflection_table.compute_background(experiments)
    reflection_table.compute_summed_intensity()
    reflection_table.compute_corrections(experiments)
    reflection_table.compute_centroid(experiments)

    profile = experiment.crystal.mosaicity
    profile.compute_partiality(experiments, reflection_table)

    return reflection_table


def refine_profile(experiment, profile, refiner_data, wavelength_spread_model="delta"):
    """Do the profile refinement"""
    logger.info("\n" + "=" * 80 + "\nRefining profile parmameters")

    # Create the parameterisation
    state = ModelState(
        experiment,
        profile.parameterisation(),
        fix_orientation=True,
        fix_unit_cell=True,
        fix_wavelength_spread=wavelength_spread_model == "delta",
    )

    # Create the refiner and refine
    refiner = ProfileRefiner(state, refiner_data)
    refiner.refine()

    # Set the profile parameters
    profile.update_model(state)
    # Set the mosaicity
    experiment.crystal.mosaicity = profile

    return refiner


def refine_crystal(
    experiment,
    profile,
    refiner_data,
    fix_unit_cell=False,
    fix_orientation=False,
    wavelength_spread_model="delta",
):
    """Do the crystal refinement"""
    if (fix_unit_cell is True) and (fix_orientation is True):
        return

    logger.info("\n" + "=" * 80 + "\nRefining crystal parmameters")

    # Create the parameterisation
    state = ModelState(
        experiment,
        profile.parameterisation(),
        fix_mosaic_spread=True,
        fix_unit_cell=fix_unit_cell,
        fix_orientation=fix_orientation,
        fix_wavelength_spread=wavelength_spread_model == "delta",
    )

    # Create the refiner and refine
    refiner = ProfileRefiner(state, refiner_data)
    refiner.refine()

    return refiner


def predict_after_potato_refinement(experiment, reflection_table):
    """
    Predict the position of the spots

    """

    # Get some stuff from experiment
    A = matrix.sqr(experiment.crystal.get_A())
    s0 = matrix.col(experiment.beam.get_s0())

    # Compute the vector to the reciprocal lattice point
    # since this is not on the ewald sphere, lets call it s2
    h = reflection_table["miller_index"]
    s1 = flex.vec3_double(len(h))
    s2 = flex.vec3_double(len(h))
    for i in range(len(reflection_table)):
        r = A * matrix.col(h[i])
        s2[i] = s0 + r
        s1[i] = matrix.col(s2[i]).normalize() * s0.length()
    reflection_table["s1"] = s1
    reflection_table["s2"] = s2
    reflection_table["entering"] = flex.bool(len(h), False)

    # Compute the ray intersections
    xyzpx = flex.vec3_double()
    xyzmm = flex.vec3_double()
    for i in range(len(s2)):
        ss = s1[i]
        mm = experiment.detector[0].get_ray_intersection(ss)
        px = experiment.detector[0].millimeter_to_pixel(mm)
        xyzpx.append(px + (0,))
        xyzmm.append(mm + (0,))
    reflection_table["xyzcal.mm"] = xyzmm
    reflection_table["xyzcal.px"] = xyzpx
    return reflection_table


def compute_prediction_probability(experiment, reflection_table):

    # Get stuff from experiment
    s0 = matrix.col(experiment.beam.get_s0())
    profile = experiment.crystal.mosaicity

    # Loop through reflections
    min_p = None
    for i in range(len(reflection_table)):
        s2 = matrix.col(reflection_table[i]["s2"])
        s3 = s2.normalize() * s0.length()
        r = s2 - s0
        epsilon = s3 - s2
        sigma = profile.sigma_for_reflection(s0, r)
        sigma_inv = sigma.inverse()
        d = (epsilon.transpose() * sigma_inv * epsilon)[0]
        p = chisq_pdf(3, d)
        if min_p is None or p < min_p:
            min_p = p

    # Print some stuff
    logger.info(
        "Quantile required to predicted all observed reflections = %.5f" % (1 - min_p)
    )


def run_potato_refinement(
    experiments,
    reflection_table,
    sigma_d,
    profile_model="angular2",
    wavelength_model="delta",
    fix_unit_cell=False,
    fix_orientation=False,
    html_output=True,
    n_cycles=3,
):
    """Runs potato refinement on strong spots.

    Creates the necessary data needed, then runs cycles of profile and crystal
    refinement,"""

    output_data = {
        "plots_data": OrderedDict(),
        "refiner_output": {
            "history": [],
            "correlation": None,
            "labels": None,
        },
    }

    # Set the M params
    if not hasattr(experiments[0].crystal, "mosaicity"):
        profile = ProfileModelFactory.from_sigma_d(profile_model, sigma_d)
    else:
        profile = experiments[0].crystal.mosaicity

    # Preprocess the reflections
    # Make some plots
    if html_output:
        output_data["plots_data"].update(
            plot_distance_from_ewald_sphere(experiments[0], reflection_table, "Initial")
        )

    # Construct the profile refiner data
    refiner_data = RefinerData.from_reflections(experiments[0], reflection_table)

    # Do the refinement
    for _ in range(n_cycles):
        # refine the profile
        refiner = refine_profile(
            experiments[0],
            profile,
            refiner_data,
            wavelength_spread_model=wavelength_model,
        )

        # Save some data for plotting later.
        output_data["refiner_output"]["history"].append(refiner.history)
        output_data["refiner_output"]["correlation"] = refiner.correlation()
        output_data["refiner_output"]["labels"] = refiner.labels()

        # refine the crystal
        _ = refine_crystal(
            experiments[0],
            profile,
            refiner_data,
            fix_unit_cell=fix_unit_cell,
            fix_orientation=fix_orientation,
            wavelength_spread_model=wavelength_model,
        )

    # Post process the reflections
    # Update predictions
    reflection_table = predict_after_potato_refinement(experiments[0], reflection_table)
    # Compute prob
    compute_prediction_probability(experiments[0], reflection_table)

    # Make some plots
    if html_output:
        output_data["plots_data"].update(
            plot_distance_from_ewald_sphere(experiments[0], reflection_table, "Final")
        )

    return experiments, reflection_table, output_data


def predict(experiments, reference, d_min=None, prediction_probability=0.9973):
    """Predict the reflections"""
    logger.info("\n" + "=" * 80 + "\nPredicting reflections")

    # Set a resolution range
    if d_min is None:
        s0 = experiments[0].beam.get_s0()
        d_min = experiments[0].detector.get_max_resolution(s0)

    # Create the index generator
    index_generator = IndexGenerator(
        experiments[0].crystal.get_unit_cell(),
        experiments[0].crystal.get_space_group().type(),
        d_min,
    )

    # Get an array of miller indices
    miller_indices_to_test = index_generator.to_array()
    logger.info("Generated %d miller indices" % len(miller_indices_to_test))

    # Get the covariance matrix
    profile = experiments[0].crystal.mosaicity

    reflection_table = profile.predict_reflections(
        experiments, miller_indices_to_test, prediction_probability
    )

    # Do the prediction
    reflection_table.compute_d(experiments)
    logger.info("Predicted %d reflections" % len(reflection_table))

    _, _, unmatched = reflection_table.match_with_reference(reference)

    # Add unmatched
    # columns = flex.std_string()
    # for col in unmatched.keys():
    #   if col in self.reflections:
    #     columns.append(col)
    # unmatched = unmatched.select(columns)
    # unmatched['id'] = flex.size_t(list(unmatched['id']))
    # self.reflections.extend(unmatched)

    return reflection_table


class Integrator(object):
    """
    Class to perform integration of stills in the following way:

    1. Do an initial integration of strong reflections
    2. Refine profile and crystal parameters
    3. Do a final integration of all reflections

    """

    def __init__(self, experiments, reflections, params=None):
        """
        Initialise the integrator

        """

        # Only use single experiment at the moment
        if len(experiments) > 1:
            raise RuntimeError("Only 1 experiment can be processed")

        # Set the parameters
        if params is not None:
            self.params = params
        else:
            self.params = phil_scope.extract(parse(""))

        # Save some stuff
        self.experiments = experiments
        self.strong = reflections
        self.reference = None
        self.reflections = None
        self.sigma_d = None
        self.plots_data = OrderedDict()

    def reindex_strong_spots(self):
        """
        Reindex the strong spot list

        """
        self.reference = reindex(
            self.strong,
            self.experiments[0],
            outlier_probability=self.params.refinement.outlier_probability,
            max_separation=self.params.refinement.max_separation,
            fail_on_bad_index=self.params.indexing.fail_on_bad_index,
        )
        if self.reference.size() < self.params.refinement.min_n_reflections:
            raise RuntimeError(
                "Too few reflections to perform refinement: got %d, expected %d"
                % (self.reference.size(), self.params.refinement.min_n_reflections)
            )

    def integrate_strong_spots(self):
        """
        Do an initial integration of the strong spots

        """
        self.reference, self.sigma_d = initial_integrator(
            self.experiments, self.reference
        )
        # Output some strong spots
        if self.params.debug.output.strong_spots:
            self.reference.as_pickle("debug.strong.pickle")
        # Print shoeboxes
        if self.params.debug.output.print_shoeboxes:
            for r in range(len(self.reference)):
                logger.info(self.reference["shoebox"][r].mask.as_numpy_array())
                logger.info(self.reference["shoebox"][r].data.as_numpy_array())

    def refine(self):
        """
        Do the refinement of profile and crystal parameters

        """

        self.experiments, self.reference, output_data = run_potato_refinement(
            self.experiments,
            self.reference,
            self.sigma_d,
            profile_model=self.params.profile.rlp_mosaicity.model,
            wavelength_model=self.params.profile.wavelength_spread.model,
            fix_unit_cell=self.params.profile.unit_cell.fixed,
            fix_orientation=self.params.profile.orientation.fixed,
            html_output=self.params.output.html,
            n_cycles=self.params.refinement.n_cycles,
        )
        self.plots_data.update(output_data["plots_data"])

        # Plot the corrgram
        if self.params.debug.output.plots:
            plt = corrgram(
                output_data["refiner_output"]["correlation"],
                output_data["refiner_output"]["labels"],
            )
            plt.savefig("corrgram.png", dpi=300)
            plt.clf()
        # Save the history
        if self.params.debug.output.history:
            with open("history.json", "w") as outfile:
                json.dump(
                    output_data["refiner_output"]["history"][-1], outfile, indent=2
                )
        # Save the profile model
        if self.params.debug.output.profile_model:
            with open("profile_model.json", "w") as outfile:
                data = {
                    "rlp_mosaicity": tuple(
                        self.experiments[0].crystal.mosaicity.sigma()
                    )
                }
                json.dump(data, outfile, indent=2)

    def predict(self):
        id_map = dict(self.strong.experiment_identifiers())

        self.reflections = predict(
            self.experiments,
            self.reference,
            d_min=self.params.prediction.d_min,
            prediction_probability=self.params.prediction.probability,
        )

        # now set the identifiers
        ids_ = set(self.reflections["id"])
        assert ids_ == set(id_map.keys()), f"{ids_}, {id_map.keys()}"
        for id_ in ids_:
            self.reflections.experiment_identifiers()[id_] = id_map[id_]

    def integrate(self):
        """
        Do an final integration of the reflections

        """
        self.reflections = final_integrator(
            self.experiments,
            self.reflections,
            self.sigma_d,
            self.params.integration.use_crude_shoebox_mask,
            self.params.integration.shoebox.probability,
        )

        from dials.algorithms.integration.report import IntegrationReport

        report = IntegrationReport(self.experiments, self.reflections)
        logger.info(report.tables[2].as_str())

        # Plot the partialities
        if self.params.output.html:
            self.plots_data.update(plot_partiality(self.reflections))

        # Delete shoeboxes if necessary
        if not self.params.debug.output.shoeboxes:
            del self.reflections["shoebox"]

        # Delete corrections if specified
        if not self.params.integration.corrections.lp:
            del self.reflections["lp"]
        if not self.params.integration.corrections.dqe:
            del self.reflections["dqe"]
        if not self.params.integration.corrections.partiality:
            del self.reflections["partiality"]
            del self.reflections["partiality.inv.variance"]


def generate_html_report(plots_data, filename):
    loader = ChoiceLoader(
        [
            PackageLoader("dials", "templates"),
            PackageLoader("dials", "static", encoding="utf-8"),
        ]
    )
    env = Environment(loader=loader)
    template = env.get_template("simple_report.html")
    html = template.render(
        page_title="DIALS SSX integration report",
        panel_title="Integration plots",
        panel_id="ewald",
        graphs=plots_data,
    )
    logger.info(f"Writing html report to {filename}")
    with open(filename, "wb") as f:
        f.write(html.encode("utf-8", "xmlcharrefreplace"))
