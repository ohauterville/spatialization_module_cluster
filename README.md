# Spatialization module

by Olivier Hauterville

### What ?

This code is a way to correlate spatial data (GIS or Earth observation data) to administrative statistical data (GDP, population, electricity consumption, car fleet, etc.).

### Why ?

We want to use spatial data because we know that our observables at the global or country scale, do not scale to smaller regions because of regional disparities and specificities. In other words, our dynamical models works well with big scale observables over time, but poorly with small scale observables over space.

Main goals are to improve the quality of our non spatial models. This means two things :

1. Being able to use our model predictions at fine scale and for different regions (*downscaling*).
2. Estimating stocks by using geospatial proxies to overcome a lack of statistical data (*upscaling*).

### How ?

In order to do so, we are trying to observe regularities along GIS data when compared to their statistical counterparts.

We use GIS data for several reasons :

1. The quantity : Earth Observation is a big field with a lot of open source data and it is increasing as our need to understand our impact on the planet is growing.
2. The quality : This data is empirical (it is mostly physical observations) and is less prone to human errors. The quality of the data can be assessed and the errors are uniform along the planet (less global north/global south inequalities).
3. The uniformity : With Earth Observation datasets, we can expand our studies across countries all over the planet.
4. The freedom of scale : GIS data may be suitable to study a small village as well as a country.
5. The freedom of area : Similarly to the point above, we may be able to study a country but also a place of interest along several administrative borders like, for example, along the Rhine River.

## Versions

### V1

The file **V1_181024.ipynb** is the last version before passing to OECD data. The Spatio Temporal Logistic function gives very good results when comparing regions of FRA and DEU. Since the results are promising, we want to explore further with a more generalized data on the administrative side (GDP, pop, other) and so I will, in V2, adapt the code to expand our study to all the subregions included in the OECD dataset.
