import { pickId, safeNumber } from "../utils.js";

export function getMediTrustElements() {
  return {
    nameEl: pickId("patientName", "name"),
    ageEl: pickId("patientAge", "age"),
    btn: pickId("checkRiskBtn", "btn"),
    downloadReportBtn: pickId("downloadReportBtn"),
    form: pickId("riskForm"),
    sexEl: pickId("sex"),
    cpEl: pickId("cp"),
    trestbpsEl: pickId("trestbps"),
    cholEl: pickId("chol"),
    fbsEl: pickId("fbs"),
    restecgEl: pickId("restecg"),
    thalachEl: pickId("thalach"),
    exangEl: pickId("exang"),
    oldpeakEl: pickId("oldpeak"),
    slopeEl: pickId("slope"),
    caEl: pickId("ca"),
    thalEl: pickId("thal"),
  };
}

export function buildPredictPayload(elements) {
  return {
    age: safeNumber(elements.ageEl?.value),
    sex: Number(elements.sexEl.value),
    cp: Number(elements.cpEl.value),
    trestbps: Number(elements.trestbpsEl.value),
    chol: Number(elements.cholEl.value),
    fbs: Number(elements.fbsEl.value),
    restecg: Number(elements.restecgEl.value),
    thalach: Number(elements.thalachEl.value),
    exang: Number(elements.exangEl.value),
    oldpeak: Number(elements.oldpeakEl.value),
    slope: Number(elements.slopeEl.value),
    ca: Number(elements.caEl.value),
    thal: Number(elements.thalEl.value),
  };
}
