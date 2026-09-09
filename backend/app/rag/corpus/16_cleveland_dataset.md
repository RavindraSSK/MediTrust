---
id: uci-cleveland-heart-disease-dataset
title: The UCI Cleveland Heart Disease data set
source: Detrano et al., International application of a new probability algorithm for the diagnosis of coronary artery disease (Am J Cardiol 1989); UCI Machine Learning Repository
organization: Cleveland Clinic Foundation; UCI Machine Learning Repository
year: 1989
url: https://doi.org/10.1016/0002-9149(89)90524-9
features: dataset
tags: dataset, Cleveland, UCI, attributes, angiography, data quality
evidence_type: primary data description
---
The Cleveland Clinic Foundation data were collected by Robert Detrano and colleagues and donated to the UCI Machine Learning Repository. Each record contains 13 clinical attributes: age, sex, chest pain type, resting blood pressure, serum cholesterol, whether fasting blood sugar exceeds 120 mg/dL, resting ECG result, maximum heart rate achieved, exercise-induced angina, exercise-induced ST depression, the slope of the peak exercise ST segment, the number of major vessels coloured by fluoroscopy and the thallium scan result, together with an angiographic outcome.

In the original data the outcome variable ranges from 0, meaning less than 50 percent diameter narrowing, to 4, and almost all published work collapses it to the presence or absence of disease. The widely used Kaggle redistribution of this file re-coded several categorical variables and inverted the outcome label; MediTrust decodes the file back to the original attribute definitions before training so that the predicted probability refers to the presence of coronary artery disease.
