import numpy
from dials.algorithms.peak_finding import smooth_2d
def do_all_2d(sweep):
    import time

    array_2d = sweep.to_array()
    data3d = array_2d.as_numpy_array()
    data2d = numpy.copy(data3d[0, :, :])
    n_row = numpy.size(data2d[:, 0:1])
    n_col = numpy.size(data2d[0:1, :])
    print 'n_frm, n_row, n_col =', n_row, n_col

    dif2d = numpy.zeros_like(data2d)
    tm = 2
    n_blocks_x = 5
    n_blocks_y = 6
    col_block_size = n_col / n_blocks_x
    row_block_size = n_row / n_blocks_y

    time1 = time.time()
    for tmp_block_x_pos in range(n_blocks_x):
        for tmp_block_y_pos in range(n_blocks_y):
            col_from = int(tmp_block_x_pos * col_block_size)
            col_to = int((tmp_block_x_pos + 1) * col_block_size)
            row_from = int(tmp_block_y_pos * row_block_size)
            row_to = int((tmp_block_y_pos + 1) * row_block_size)
            tmp_dat2d = numpy.copy(data2d[row_from:row_to, col_from:col_to])
            tmp_dif2d = find_mask_2d(tmp_dat2d, tm)
            dif2d[row_from:row_to, col_from:col_to] = tmp_dif2d[:, :]

    print 'time.time() =', time.time()
    time2 = time.time()
    time_dif = time2 - time1
    print time2, ' - ', time1, '=', time_dif
    time1 = time2

    dif_2d_ext = find_ext_mask_2d(dif2d)
    x_from_lst, x_to_lst, y_from_lst, y_to_lst = find_bound_2d(dif_2d_ext)

    from matplotlib import pylab, cm
    plt = pylab.imshow(data2d , vmin = 0, vmax = 1000, cmap = cm.Greys_r, interpolation = 'nearest', origin = 'lower')
    pylab.scatter(x_from_lst, y_from_lst, marker = 'x')
    pylab.scatter(x_to_lst, y_to_lst, marker = 'x')
    pylab.show()

    return x_from_lst, x_to_lst, y_from_lst, y_to_lst

def find_mask_2d(data2d, n_times):
    from scitbx.array_family import flex
    n_col = numpy.size(data2d[0:1, :])
    n_row = numpy.size(data2d[:, 0:1])

    data2dsmoth = numpy.zeros_like(data2d)
    diffdata2d = numpy.zeros_like(data2d)
    data2dtmp = numpy.copy(data2d)
    if n_times > 0:

        data2dsmoth = smooth_2d(flex.int(data2d), 5).as_numpy_array()

    else:
        promedio = numpy.mean(data2d)
        data2dsmoth[:, :] = promedio
        print 'promedio =', promedio

#######################################################################################################
    #cont = 0                                                                  # This way to calculate
    #dif_tot = 0                                                               # this magical variable
    #for row in range(0, n_row, 1):                                            # is more statistical
    #    for col in range(0, n_col, 1):                                        # and seems to be giving
    #        cont += 1                                                         # better results
    #        dif_tot += numpy.abs(data2d[row, col] - data2dsmoth[row, col])    #
    #dif_avg = dif_tot / cont                                                  #
    ##print 'dif_avg=', dif_avg                                                #
#######################################################################################################

    threshold_shift = 10

    data2dsmoth[:, :] = data2dsmoth[:, :] + threshold_shift

    for row in range(0, n_row, 1):
        for col in range(0, n_col, 1):
            if data2d[row, col] > data2dsmoth[row, col]:
#            if data2d[row, col] > 20:
                diffdata2d[row, col] = 1

    from matplotlib import pyplot as plt                                        #                             to be removed
    plt.imshow(data2d, interpolation = "nearest", origin = 'lower')             #                             to be removed
    plt.show()                                                                  #                             to be removed
    plt.imshow(data2dsmoth, interpolation = "nearest", origin = 'lower')        #                             to be removed
    plt.show()                                                                  #                             to be removed
    plt.imshow(diffdata2d, interpolation = "nearest", origin = 'lower')         #                             to be removed
    plt.show()                                                                  #                             to be removed

    return diffdata2d
def find_ext_mask_3d(diffdata3d):
    n_frm = numpy.size(diffdata3d[:, 0:1, 0:1])
    n_row = numpy.size(diffdata3d[0:1, :, 0:1])
    n_col = numpy.size(diffdata3d[0:1, 0:1, :])
    ext_area = 1
    diffdata3d_ext = numpy.zeros_like(diffdata3d)

    for frm in range(ext_area, n_frm - ext_area + 1, 1):
        for row in range(ext_area, n_row - ext_area + 1, 1):
            for col in range(ext_area, n_col - ext_area + 1, 1):
                if diffdata3d[frm, row, col] == 1:
                    diffdata3d_ext[frm - ext_area:frm + ext_area + 1, row - ext_area:row + ext_area + 1, col - ext_area:col + ext_area + 1] = 1
    return diffdata3d_ext

def find_ext_mask_2d(diffdata2d):
    n_row = numpy.size(diffdata2d[:, 0:1])
    n_col = numpy.size(diffdata2d[0:1, :])
    ext_area = 1
    diffdata2d_ext = numpy.zeros_like(diffdata2d)
    for row in range(ext_area, n_row - ext_area + 1, 1):
        for col in range(ext_area, n_col - ext_area + 1, 1):
            if diffdata2d[row, col] == 1:
                diffdata2d_ext[row - ext_area:row + ext_area + 1, col - ext_area:col + ext_area + 1] = 1
    return diffdata2d_ext

def find_bound_2d(mask):
    n_col = numpy.size(mask[0:1, :])
    n_row = numpy.size(mask[:, 0:1])
    #tmp_mask = numpy.zeros(n_row * n_col, dtype = int).reshape(n_row, n_col)
    #tmp_mask[:, :] = mask[:, :]

    tmp_mask = numpy.copy(mask)

    x_from_lst = []
    x_to_lst = []
    y_from_lst = []
    y_to_lst = []

    for row in range(0, n_row, 1):
        for col in range(0, n_col, 1):
            if tmp_mask[row, col] == 1:
                lft_bound = col - 1
                rgt_bound = col + 1
                bot_bound = row - 1
                top_bound = row + 1

                bot_old = 0
                top_old = 0
                lft_old = 0
                rgt_old = 0
                in_img = "True"
                while in_img == "True":


                    # left wall
                    if lft_bound >= 0 and top_bound < n_row and bot_bound >= 0:
                        for scan_row in range(bot_bound, top_bound + 1, 1):
                            if tmp_mask[scan_row, lft_bound] == 1:
                                lft_bound -= 1
                                break
                    else:
                        in_img = "false"
                        break

                    # right wall
                    if rgt_bound < n_col and top_bound < n_row and bot_bound >= 0:
                        for scan_row in range(bot_bound, top_bound + 1, 1):
                            if tmp_mask[scan_row, rgt_bound] == 1:
                                rgt_bound += 1
                                break
                    else:
                        in_img = "false"
                        break

                    # bottom wall
                    if bot_bound >= 0 and lft_bound >= 0 and rgt_bound < n_col:
                        for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                            if tmp_mask[bot_bound, scan_col] == 1:
                                bot_bound -= 1
                                break
                    else:
                        in_img = "false"
                        break

                    # top wall
                    if top_bound < n_row and lft_bound >= 0 and rgt_bound < n_col:
                        for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                            if tmp_mask[top_bound, scan_col] == 1:
                                top_bound += 1
                                break
                    else:
                        in_img = "false"
                        break
                    if bot_bound == bot_old and top_bound == top_old and lft_bound == lft_old and rgt_bound == rgt_old:
                        break
                    bot_old = bot_bound
                    top_old = top_bound
                    lft_old = lft_bound
                    rgt_old = rgt_bound

                #lst_coord.append([bot_bound, lft_bound, top_bound, rgt_bound])
                tmp_mask[bot_bound:top_bound, lft_bound:rgt_bound] = 0
                if  in_img == "True":
                    x_from_lst.append(lft_bound)
                    x_to_lst.append(rgt_bound)
                    y_from_lst.append(bot_bound)
                    y_to_lst.append(top_bound)

    return x_from_lst, x_to_lst, y_from_lst, y_to_lst

def find_bound_3d(diffdata3d):
    n_frm = numpy.size(diffdata3d[:, 0:1, 0:1])
    n_row = numpy.size(diffdata3d[0:1, :, 0:1])
    n_col = numpy.size(diffdata3d[0:1, 0:1, :])

    tmp_3d_mask = numpy.zeros(n_row * n_col * n_frm , dtype = int).reshape(n_frm, n_row, n_col)
    tmp_3d_mask[:, :, :] = diffdata3d[:, :, :]
    x_from_lst = []
    x_to_lst = []
    y_from_lst = []
    y_to_lst = []
    z_from_lst = []
    z_to_lst = []
    for frm in range(0, n_frm, 1):
        for row in range(0, n_row, 1):
            for col in range(0, n_col, 1):
                if tmp_3d_mask[frm, row, col] == 1:
                    bck_bound = frm - 1
                    frn_bound = frm + 1
                    lft_bound = col - 1
                    rgt_bound = col + 1
                    bot_bound = row - 1
                    top_bound = row + 1

                    bck_old = 0
                    frn_old = 0
                    bot_old = 0
                    top_old = 0
                    lft_old = 0
                    rgt_old = 0
                    in_img = "True"
                    while in_img == "True":

                        # left wall
                        if lft_bound >= 0 and top_bound < n_row and bot_bound >= 0 and frn_bound < n_frm and bck_bound >= 0:
                            stay_in = "True"
                            for scan_row in range(bot_bound, top_bound + 1, 1):
                                for scan_frm in range(bck_bound, frn_bound + 1, 1):
                                    if tmp_3d_mask[scan_frm, scan_row, lft_bound] == 1:
                                        lft_bound -= 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break

                        # right wall
                        if rgt_bound < n_col and top_bound < n_row and bot_bound >= 0 and frn_bound < n_frm and bck_bound >= 0:
                            stay_in = "True"
                            for scan_row in range(bot_bound, top_bound + 1, 1):
                                for scan_frm in range(bck_bound, frn_bound + 1, 1):
                                    if tmp_3d_mask[scan_frm, scan_row, rgt_bound] == 1:
                                        rgt_bound += 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break

                        # bottom wall
                        if bot_bound >= 0 and lft_bound >= 0 and rgt_bound < n_col and frn_bound < n_frm and bck_bound >= 0:
                            stay_in = "True"
                            for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                                for scan_frm in range(bck_bound, frn_bound + 1, 1):
                                    if tmp_3d_mask[scan_frm, bot_bound, scan_col] == 1:
                                        bot_bound -= 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break
                        # top wall
                        if top_bound < n_row and lft_bound >= 0 and rgt_bound < n_col and frn_bound < n_frm and bck_bound >= 0:
                            stay_in = "True"
                            for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                                for scan_frm in range(bck_bound, frn_bound + 1, 1):
                                    if tmp_3d_mask[scan_frm, top_bound, scan_col] == 1:
                                        top_bound += 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break

                        # front wall
                        if frn_bound < n_frm and lft_bound >= 0 and rgt_bound < n_col and top_bound < n_row and bot_bound >= 0:
                            stay_in = "True"
                            for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                                for scan_row in range(bot_bound, top_bound + 1, 1):
                                    if tmp_3d_mask[frn_bound, scan_row, scan_col] == 1:
                                        frn_bound += 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break

                        # back wall
                        if bck_bound >= 0 and lft_bound >= 0 and rgt_bound < n_col and top_bound < n_row and bot_bound >= 0:
                            stay_in = "True"
                            for scan_col in range(lft_bound, rgt_bound + 1 , 1):
                                for scan_row in range(bot_bound, top_bound + 1, 1):
                                    if tmp_3d_mask[bck_bound, scan_row, scan_col] == 1:
                                        bck_bound -= 1
                                        stay_in = "False"
                                        break
                                if stay_in == "False":
                                    break
                        else:
                            in_img = "false"
                            break

                        if bot_bound == bot_old and top_bound == top_old and lft_bound == lft_old and rgt_bound == rgt_old and bck_bound == bck_old and frn_bound == frn_old:
                            break
                        bot_old = bot_bound
                        top_old = top_bound
                        lft_old = lft_bound
                        rgt_old = rgt_bound
                        bck_old = bck_bound
                        frn_old = frn_bound
                    #lst_coord.append([bot_bound, lft_bound, top_bound, rgt_bound])

                    if  in_img == "True":
                        tmp_3d_mask[bck_bound:frn_bound, bot_bound:top_bound, lft_bound:rgt_bound] = 0
                        x_from_lst.append(lft_bound)
                        x_to_lst.append(rgt_bound)
                        y_from_lst.append(bot_bound)
                        y_to_lst.append(top_bound)
                        z_from_lst.append(bck_bound)
                        z_to_lst.append(frn_bound)

    return x_from_lst, x_to_lst, y_from_lst, y_to_lst, z_from_lst, z_to_lst
