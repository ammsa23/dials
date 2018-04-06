from __future__ import absolute_import, division, print_function

from libtbx.test_utils.pytest import discover

tst_list = [
    "$B/test/algorithms/spatial_indexing/tst_collision_detection",
    "$B/test/algorithms/spatial_indexing/tst_octree",
    "$B/test/algorithms/spatial_indexing/tst_quadtree",
    "$B/test/algorithms/spot_prediction/tst_reeke_model",
    "$D/test/algorithms/background/tst_modeller.py",
    "$D/test/algorithms/generate_test_reflections/tst_generate_test_refl.py",
    "$D/test/algorithms/image/connected_components/tst_connected_components.py",
    "$D/test/algorithms/image/fill_holes/tst_simple_fill.py",
    "$D/test/algorithms/image/filter/tst_distance.py",
    "$D/test/algorithms/image/filter/tst_index_of_dispersion.py",
    "$D/test/algorithms/image/filter/tst_mean_and_variance.py",
    "$D/test/algorithms/image/filter/tst_median.py",
    "$D/test/algorithms/image/filter/tst_summed_area.py",
    "$D/test/algorithms/image/threshold/tst_local.py",
    "$D/test/algorithms/image/tst_centroid.py",
    "$D/test/algorithms/integration/profile/tst_circle_sampler.py",
    "$D/test/algorithms/integration/profile/tst_empirical_modeller.py",
    "$D/test/algorithms/integration/profile/tst_grid_sampler.py",
    "$D/test/algorithms/integration/profile/tst_multi_experiment_modeller.py",
    "$D/test/algorithms/integration/profile/tst_profile_fitting.py",
    "$D/test/algorithms/integration/profile/tst_single_sampler.py",
    "$D/test/algorithms/integration/tst_filter_overlaps.py",
    "$D/test/algorithms/polygon/clip/tst_clipping.py",
    "$D/test/algorithms/polygon/tst_spatial_interpolation.py",
    "$D/test/algorithms/profile_model/tst_profile_model.py",
    "$D/test/algorithms/refinement/tst_detector_parameters.py",
    "$D/test/algorithms/refinement/tst_goniometer_parameters.py",
    "$D/test/algorithms/refinement/tst_finite_diffs.py",
    "$D/test/algorithms/refinement/tst_hierarchical_detector_refinement.py",
    "$D/test/algorithms/refinement/tst_multi_experiment_refinement.py",
    "$D/test/algorithms/refinement/tst_multi_panel_detector_parameterisation.py",
    "$D/test/algorithms/refinement/tst_prediction_parameters.py",
    "$D/test/algorithms/refinement/tst_ref_passage_categorisation.py",
    "$D/test/algorithms/refinement/tst_refine_multi_stills.py",
    "$D/test/algorithms/refinement/tst_refine_multi_wedges.py",
    "$D/test/algorithms/refinement/tst_refinement_regression.py",
    "$D/test/algorithms/refinement/tst_rotation_decomposition.py",
    "$D/test/algorithms/refinement/tst_scan_varying_model_parameters.py",
    "$D/test/algorithms/refinement/tst_scan_varying_prediction_parameters.py",
    "$D/test/algorithms/refinement/tst_stills_prediction_parameters.py",
    "$D/test/algorithms/refinement/tst_stills_refinement.py",
    "$D/test/algorithms/refinement/tst_stills_spherical_relp_derivatives.py",
    "$D/test/algorithms/refinement/tst_restraints_parameterisation.py",
    "$D/test/algorithms/refinement/tst_restraints_gradients.py",
    "$D/test/algorithms/refinement/tst_sv_multi_panel_refinement.py",
    "$D/test/algorithms/refinement/tst_xfel_metrology.py",
    "$D/test/algorithms/refinement/tst_angle_derivatives_wrt_vector_elts.py",
    "$D/test/algorithms/reflection_basis/tst_coordinate_system.py",
    "$D/test/algorithms/reflection_basis/tst_map_frames.py",
    "$D/test/algorithms/reflection_basis/tst_transform.py",
    "$D/test/algorithms/shoebox/tst_find_overlapping.py",
    "$D/test/algorithms/shoebox/tst_mask_foreground.py",
    "$D/test/algorithms/shoebox/tst_mask_overlapping.py",
    "$D/test/algorithms/shoebox/tst_partiality_calculator.py",
    "$D/test/algorithms/spatial_indexing/tst_spatial_index.py",
    "$D/test/algorithms/spot_prediction/tst_index_generator.py",
    "$D/test/algorithms/spot_prediction/tst_pixel_to_miller_index.py",
    "$D/test/algorithms/spot_prediction/tst_ray_predictor.py",
    "$D/test/algorithms/spot_prediction/tst_reeke_index_generator.py",
    "$D/test/algorithms/spot_prediction/tst_rotation_angles.py",
    "$D/test/algorithms/spot_prediction/tst_scan_static_reflection_predictor.py",
    "$D/test/algorithms/spot_prediction/tst_scan_varying_predictor.py",
    "$D/test/algorithms/spot_prediction/tst_scan_varying_reflection_predictor.py",
    "$D/test/algorithms/spot_prediction/tst_spot_prediction.py",
    "$D/test/algorithms/spot_prediction/tst_stills_reflection_predictor.py",
    "$D/test/algorithms/scaling/tst_observation_manager.py",
    "$D/test/algorithms/scaling/tst_scale_parameterisation.py",
    "$D/test/algorithms/scaling/tst_HRS_derivatives.py",
    "$D/test/array_family/tst_flex_shoebox.py",
    "$D/test/command_line/tst_export_bitmaps.py",
    "$D/test/command_line/tst_export_best.py",
    "$D/test/command_line/tst_filter_reflections.py",
    "$D/test/command_line/tst_find_spots_server_client.py",
    "$D/test/command_line/tst_generate_mask.py",
    "$D/test/command_line/tst_idials.py",
    "$D/test/command_line/tst_import_xds.py",
    "$D/test/command_line/tst_merge_cbf.py",
    "$D/test/command_line/tst_merge_reflection_lists.py",
    "$D/test/command_line/tst_plot_scan_varying_crystal.py",
    "$D/test/command_line/tst_predict.py",
    "$D/test/command_line/tst_refine.py",
    "$D/test/command_line/tst_rs_mapper.py",
    "$D/test/command_line/tst_show_extensions.py",
    "$D/test/command_line/tst_sort_reflections.py",
    "$D/test/command_line/tst_spot_counts_per_image.py",
    "$D/test/command_line/tst_stereographic_projections.py",
    "$D/test/command_line/tst_stills_detector_hybrid_refine.py",
    "$D/test/command_line/tst_stills_process.py",
    "$D/test/framework/tst_interface.py",
    "$D/test/model/data/tst_pixel_list.py",
    "$D/test/model/data/tst_prediction.py",
    "$D/test/model/data/tst_shoebox.py",
    "$D/test/tst_phil.py",
    ] + discover()
