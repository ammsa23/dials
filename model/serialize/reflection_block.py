
from __future__ import division

class ReflectionBlockExtractor(object):
  ''' A class to extract blocks of reflections. '''

  def __init__(self, filename, imageset, reflections, nblocks,
               gain=None, dark=None, mask=None):
    ''' Initialise the extractor. '''
    from dials.model.serialize import extract_shoeboxes_to_file
    from dials.model.serialize import ShoeboxBlockImporter
    from dials.array_family import flex

    # Filter the reflections
    self.reflections = self._filter_reflections(reflections)

    # Extract the shoeboxes to file
    extract_shoeboxes_to_file(filename, imageset, reflections)

    # Calculate the blocks
    self._blocks = self._compute_blocks(len(imageset), nblocks)

    # Construct the importer
    z = self.reflections['xyzcal.px'].parts()[2]
    if gain and dark and mask:
      self._importer = ShoeboxBlockImporter(
        filename, flex.size_t(self._blocks), z, gain, dark, mask)
    else:
      self._importer = ShoeboxBlockImporter(
        filename, flex.size_t(self._blocks), z)

  def block(self, index):
    ''' Get the block. '''
    return tuple(self._blocks[index:index+1])

  def __len__(self):
    ''' Return the number of blocks. '''
    return len(self._importer)

  def __getitem__(self, index):
    ''' Get a block of reflections. '''
    from dials.util.command_line import Command

    # Get the indices and shoeboxes
    Command.start('Extracting block %d' % index)
    indices, shoeboxes = self._importer[index]

    # Create the partial array of reflections
    reflections = self.reflections.select(indices)
    reflections['shoebox'] = shoeboxes
    nref = len(reflections)
    Command.end('Extracted %d reflections from block %d' % (nref, index))

    # return the indices and reflections
    return indices, reflections

  def __iter__(self):
    ''' Iterate through the blocks. '''
    for i in range(len(self)):
      yield self[i]

  def _filter_reflections(self, reflections):
    ''' Filter the reflections and sort them by z. '''
    from dials.array_family import flex

    # Sort the reflections by z
    z = reflections['xyzcal.px'].parts()[2]
    indices = flex.size_t(sorted(range(len(z)), key=lambda x: z[x]))
    reflections.reorder(indices)

    # Return the reflections
    return reflections

  def _compute_blocks(self, nframes, nblocks):
    ''' Compute the number of blocks. '''
    from math import ceil
    blocks = [0]
    assert(nblocks <= nframes)
    block_length = int(ceil(nframes / nblocks))
    for i in range(nblocks):
      frame = (i + 1) * block_length
      if frame > nframes:
        frame = nframes
      blocks.append(frame)
      if frame == nframes:
        break
    assert(all(b > a for a, b in zip(blocks, blocks[1:])))
    return blocks
