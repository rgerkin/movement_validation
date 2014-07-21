# -*- coding: utf-8 -*-
"""

"""

import numpy as np

from .. import utils
from .. import config

from . import feature_comparisons as fc
# To avoid conflicting with variables named 'velocity', we 
# import this as 'velocity_module':
from . import velocity as velocity_module 

class Range(object):

    """
    Attributes
    ------------------
    value :

    """

    def __init__(self, contour_x=None, contour_y=None):

        if contour_x is None:
            return

        # Get average per frame
        #------------------------------------------------
        mean_cx = contour_x.mean(axis=0)
        mean_cy = contour_y.mean(axis=0)

        # Average over all frames for subtracting
        #-------------------------------------------------
        x_centroid_cx = np.nanmean(mean_cx)
        y_centroid_cy = np.nanmean(mean_cy)

        self.value = np.sqrt(
            (mean_cx - x_centroid_cx) ** 2 + (mean_cy - y_centroid_cy) ** 2)

    @staticmethod
    def from_disk(path_var):

        # path_features.Range.from_disk(path_var)

        temp = Range(None)

        # NOTE: This is of size nx1 for Matlab versions, might want to fix on loading
        #
        temp.value = np.squeeze(path_var['range'].value)

        return temp

    def __repr__(self):
        return utils.print_object(self)

    def __eq__(self, other):

        return fc.corr_value_high(self.value, other.value, 'path.range', 0.99)


class Duration(object):

    """
    Attributes:
    -----------
    arena : Arena
    worm  : DurationElement
    head  : DurationElement
    midbody : DurationElement
    tail : DurationElement

    """

    def __init__(self, nw=None, sx=None, sy=None, widths=None, fps=None):

        if nw is None:
            return

        s_points = [nw.worm_partitions[x]
                    for x in ('all', 'head', 'body', 'tail')]

        # Return early if necessary
        #----------------------------------------------------------------------
        if len(sx) == 0 or np.isnan(sx).all():
            raise Exception('This code is not yet translated')
            #ar = Arena(create_null = True)
            #    NAN_cell  = repmat({NaN},1,n_points);
            #     durations = struct('indices',NAN_cell,'times',NAN_cell);
            #    obj.duration = h__buildOutput(arena,durations);
            #    return;

        if config.MIMIC_OLD_BEHAVIOUR:
            s_points_temp = [nw.worm_partitions[x]
                             for x in ('head', 'midbody', 'tail')]
            temp_widths   = [widths[x[0]:x[1], :] for x in s_points_temp]
            mean_widths = [np.nanmean(x.reshape(x.size)) for x in temp_widths]
            mean_width = np.mean(mean_widths)
        else:
            mean_width = np.nanmean(widths)

        scale = 2.0 ** 0.5 / mean_width

        # Scale the skeleton and translate so that the minimum values are at 1
        #----------------------------------------------------------------------
        with np.errstate(invalid='ignore'):
            # This is different between Matlab and Numpy
            scaled_sx = np.round(sx * scale)
            scaled_sy = np.round(sy * scale)

        x_scaled_min = np.nanmin(scaled_sx)
        x_scaled_max = np.nanmax(scaled_sx)
        y_scaled_min = np.nanmin(scaled_sy)
        y_scaled_max = np.nanmax(scaled_sy)

        # Unfortunately needing to typecast to int for array indexing also
        # removes my ability to identify invalid values :/
        # Thus we precompute invalid values and then cast
        isnan_mask = np.isnan(scaled_sx)

        scaled_zeroed_sx = (scaled_sx - x_scaled_min).astype(int)
        scaled_zeroed_sy = (scaled_sy - y_scaled_min).astype(int)

        arena_size = [
            y_scaled_max - y_scaled_min + 1, x_scaled_max - x_scaled_min + 1]
        ar = Arena(sx, sy, arena_size)

        #----------------------------------------------------------------------
        def h__populateArenas(arena_size, sys, sxs, s_points, isnan_mask):
            """

            Attributes:
            ----------------------------
            arena_size: list
              [2]
            sys : numpy.int32
              [49, n_frames]
            sxs : numpy.int32
              [49, n_frames]
            s_points: list
              [4]
            isnan_mask: bool
              [49, n_frames]


            """

            # NOTE: All skeleton points have been rounded to integer values for
            # assignment to the matrix based on their values being treated as
            # indices

            # Filter out frames which have no valid values
            #----------------------------------------------------------
            frames_run = np.flatnonzero(np.any(~isnan_mask, axis=0))
            n_frames_run = len(frames_run)

            # 1 area for each set of skeleton indices
            #-----------------------------------------
            n_points = len(s_points)
            arenas = [None] * n_points

            # Loop over the different regions of the body
            #------------------------------------------------
            for iPoint in range(n_points):

                temp_arena = np.zeros(arena_size)
                s_indices = s_points[iPoint]

                # For each frame, add +1 to the arena each time a chunk of the skeleton
                # is located in that part
                #--------------------------------------------------------------
                for iFrame in range(n_frames_run):
                    cur_frame = frames_run[iFrame]
                    cur_x = sxs[s_indices[0]:s_indices[1], cur_frame]
                    cur_y = sys[s_indices[0]:s_indices[1], cur_frame]
                    temp_arena[cur_y, cur_x] += 1

                arenas[iPoint] = temp_arena[::-1, :] #FLip axis to maintain
                # consistency with Matlab

            return arenas
        #----------------------------------------------------------------------

        temp_arenas = h__populateArenas(
            arena_size, scaled_zeroed_sy, scaled_zeroed_sx, s_points, isnan_mask)

        # For looking at the data
        #------------------------------------
        # utils.imagesc(temp_arenas[0])

        temp_duration = [DurationElement(x, fps) for x in temp_arenas]

        self.arena = ar
        self.worm = temp_duration[0]
        self.head = temp_duration[1]
        self.midbody = temp_duration[2]
        self.tail = temp_duration[3]

    def __eq__(self, other):

        if config.MIMIC_OLD_BEHAVIOUR:
            # JAH: I've looked at the results and they look right
            # Making them look the same would make things really ugly as it means
            # making rounding behavior the same between numpy and Matlab :/
            return True
        else:
            return \
                self.arena   == other.arena     and \
                self.worm    == other.worm      and \
                self.head    == other.head      and \
                self.midbody == other.midbody   and \
                self.tail == other.tail

    def __repr__(self):
        return utils.print_object(self)

    @staticmethod
    def from_disk(duration_group):

        # path_features.Duration.from_disk(path_var)

        temp = Duration(None)
        temp.arena = Arena.from_disk(duration_group['arena'])
        temp.worm = DurationElement.from_disk(duration_group['worm'])
        temp.head = DurationElement.from_disk(duration_group['head'])
        temp.midbody = DurationElement.from_disk(duration_group['midbody'])
        temp.tail = DurationElement.from_disk(duration_group['tail'])

        return temp


class DurationElement(object):

    def __init__(self, arena_coverage=None, fps=None):

        # TODO: Pass in name for __eq__

        if arena_coverage is None:
            return

        arena_coverage_r = np.reshape(arena_coverage, arena_coverage.size, 'F')
        self.indices = np.nonzero(arena_coverage_r)[0]
        self.times = arena_coverage_r[self.indices] / fps

        #wtf3 = np.nonzero(arena_coverage)

        #self.indices = np.transpose(np.nonzero(arena_coverage))
        #self.times   = arena_coverage[self.indices[:,0],self.indices[:,1]]/fps

    def __repr__(self):
        return utils.print_object(self)

    def __eq__(self, other):

        return \
            fc.corr_value_high(self.indices, other.indices, 'Duration.indices') and \
            fc.corr_value_high(self.times, other.times, 'Duration.times')

    @classmethod
    def from_disk(cls, saved_duration_elem):

        self = cls.__new__(cls)
        self.indices = saved_duration_elem['indices'].value[0]
        self.times = saved_duration_elem['times'].value[0]

        return self


class Arena(object):

    """

    This is constructed from the Duration constructor.
    """

    def __init__(self, sx, sy, arena_size, create_null=False):

        if create_null:
            self.height = np.nan
            self.width = np.nan
            self.min_x = np.nan
            self.min_y = np.nan
            self.max_x = np.nan
            self.max_y = np.nan
        else:
            self.height = arena_size[0]
            self.width = arena_size[1]
            self.min_x = np.nanmin(sx)
            self.min_y = np.nanmin(sy)
            self.max_x = np.nanmax(sx)
            self.max_y = np.nanmax(sy)

    def __eq__(self, other):
        # NOTE: Due to rounding differences between Matlab and numpy
        # the height and width values are different by 1
        return \
            fc.fp_isequal(self.height, other.height, 'Arena.height', 1) and \
            fc.fp_isequal(self.width, other.width, 'Arena.width', 1)   and \
            fc.fp_isequal(self.min_x, other.min_x, 'Arena.min_x')   and \
            fc.fp_isequal(self.min_y, other.min_y, 'Arena.min_y')   and \
            fc.fp_isequal(self.max_x, other.max_x, 'Arena.max_x')   and \
            fc.fp_isequal(self.max_y, other.max_y, 'Arena.max_y')

    def __repr__(self):
        return utils.print_object(self)

    @classmethod
    def from_disk(cls, saved_arena_elem):

        self = cls.__new__(cls)
        self.height = saved_arena_elem['height'].value[0, 0]
        self.width = saved_arena_elem['width'].value[0, 0]
        self.min_x = saved_arena_elem['min']['x'].value[0, 0]
        self.min_y = saved_arena_elem['min']['y'].value[0, 0]
        self.max_x = saved_arena_elem['max']['x'].value[0, 0]
        self.max_y = saved_arena_elem['max']['y'].value[0, 0]

        return self


def worm_path_curvature(x, y, fps, ventral_mode):
    """
    Parameters:
    -----------
    x : 
      Worm skeleton x coordinates, []

    """

    # https://github.com/JimHokanson/SegwormMatlabClasses/blob/master/%2Bseg_worm/%2Bfeatures/%40path/wormPathCurvature.m

    BODY_I = slice(44, 3, -1)

    # This was nanmean but I think mean will be fine. nanmean was
    # causing the program to crash
    diff_x = np.mean(np.diff(x[BODY_I, :], axis=0), axis=0)
    diff_y = np.mean(np.diff(y[BODY_I, :], axis=0), axis=0)
    avg_body_angles_d = np.arctan2(diff_y, diff_x) * 180 / np.pi

    # NOTE: This is what is in the MRC code, but differs from their description.
    # In this case I think the skeleton filtering makes sense so we'll keep it.
    speed, ignored_variable, motion_direction = \
        velocity_module.compute_velocity(x[BODY_I, :], y[BODY_I,:], \
                                         avg_body_angles_d, config.BODY_DIFF, ventral_mode)

    frame_scale = velocity_module.get_frames_per_sample(config.BODY_DIFF)
    half_frame_scale = (frame_scale - 1) / 2

    # Compute the angle differentials and distances.
    speed = np.abs(speed)

    # At each frame, we'll compute the differences in motion direction using
    # some frame in the future relative to the current frame
    #
    #i.e. diff_motion[current_frame] = motion_direction[current_frame + frame_scale] - motion_direction[current_frame]
    #------------------------------------------------
    diff_motion = np.empty(speed.shape)
    diff_motion[:] = np.NAN

    right_max_I = len(diff_motion) - frame_scale
    diff_motion[0:(right_max_I + 1)] = motion_direction[(frame_scale - 1):] - motion_direction[0:(right_max_I + 1)]

    with np.errstate(invalid='ignore'):
        diff_motion[diff_motion >= 180] -= 360
        diff_motion[diff_motion <= -180] += 360

    distance_I_base = slice(half_frame_scale, -(frame_scale + 1), 1)
    distance_I_shifted = slice(half_frame_scale + frame_scale, -1, 1)

    distance = np.empty(speed.shape)
    distance[:] = np.NaN

    distance[distance_I_base] = speed[distance_I_base] + \
        speed[distance_I_shifted] * config.BODY_DIFF / 2

    with np.errstate(invalid='ignore'):
        distance[distance < 1] = np.NAN

    return (diff_motion / distance) * (np.pi / 180)