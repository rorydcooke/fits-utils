from fits_utils import *

def main():
    z_points = {'u' : 27.075, 'g' : 29.719, 'r' : 30.236}
    catalog = np.loadtxt('cat/ugr.cat')
    corr_catalog = np.loadtxt('cat/de_reddened_combined.cat')
    r_mag, r_err, g_mag, g_err, u_mag, u_err = load_cat('cat/ugr.cat',
                                                        z_points['r'],
                                                        z_points['g'],
                                                        z_points['u'])

    color_ug = u_mag - g_mag
    color_gr = g_mag - r_mag
    corr_r_mag, corr_g_mag, corr_u_mag = corr_catalog[:,0], corr_catalog[:,1], corr_catalog[:,2]
    corr_color_ug = corr_u_mag - corr_g_mag
    corr_color_gr = corr_g_mag - corr_r_mag

    pleiades_data = np.loadtxt('pleiades/pleiadescutoff.txt')
    pleiades_gr, pleiades_ug = pleiades_data[:,0], pleiades_data[:,1]
    pleiades_cutoff = np.stack((pleiades_gr, pleiades_ug),axis=1)
    pleiades_cutoff = pleiades_cutoff[pleiades_cutoff[:,0] < 0.215]
    pleiades_fit = np.polyfit(pleiades_cutoff[:,0], pleiades_cutoff[:,1], 2)
    trendline = np.poly1d(pleiades_fit)
    trend_vals = np.linspace(-0.6, 0.6, 1000)

    plts = {'Pleiades Data' : (pleiades_gr, pleiades_ug, 'o'),
            'M52 Uncorrected' : (color_gr, color_ug, 'o'),
            'Pleiades 2nd Order Best Fit Line' : (pleiades_cutoff[:,0],
                                        trendline(pleiades_cutoff[:,0]), '-')}
    plot_diagram(plts, x_label='Color: (g - r)', y_label='Color: (u - g)',
                 sup_title='Color-Color Diagram \n M52', legend=True,
                 filename='M52_color_color_uncorrected_2o')

    # plot_HR(color_gr, color_ug, 'Color: G-R', 'Color: U-G', 'M52')

if __name__ == '__main__':
    main()
