---
id: meditrust-model-methods-limitations
title: How the MediTrust risk model works and its limitations
source: Lundberg and Lee, A Unified Approach to Interpreting Model Predictions (NeurIPS 2017); UCI Machine Learning Repository, Heart Disease data set; MediTrust model card
organization: MediTrust project
year: 2026
url: https://archive.ics.uci.edu/dataset/45/heart+disease
features: methods
tags: SHAP, explainability, model limitations, validation, decision support, dataset
evidence_type: methods documentation
---
SHAP (SHapley Additive exPlanations) attributes the difference between an individual prediction and the average prediction to each input feature using a cooperative game-theory framework. Positive SHAP values push the estimated probability of disease upward and negative values pull it downward, and the contributions add up to the final predicted probability, which is why the MediTrust interface can show a waterfall from the base rate to the patient's estimate.

The training data is the UCI Cleveland Heart Disease data set: 303 patients evaluated at the Cleveland Clinic in 1988, of whom roughly 46 percent had angiographic coronary disease. The data set is small, decades old, drawn from a population referred for coronary angiography and lacks contemporary biomarkers such as high-sensitivity troponin. The model has not been validated in a modern emergency department population, so its outputs must be treated as decision support rather than diagnosis.

Model probabilities are mapped to Low, Medium and High bands using thresholds selected on cross-validated predictions to keep sensitivity high for the rule-out band and specificity high for the rule-in band. A Low band does not exclude coronary disease and a High band is not a diagnosis; both should be interpreted alongside the clinical examination, ECG, vital signs and laboratory results.
