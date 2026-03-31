import { safeNumber } from "../utils.js";
import { predictRisk, assessRisk } from "../services/api.js";
import { renderError, clearError, renderRiskResult } from "./render.js";
import { buildPredictPayload } from "./form.js";

export async function handlePrediction(elements) {
  clearError();

  const name = (elements.nameEl?.value || "").trim();
  const age = safeNumber(elements.ageEl?.value);

  if (!name) return renderError("Please enter patient name.");
  if (age === null || age < 1 || age > 120) {
    return renderError("Please enter a valid age (1–120).");
  }

  if (elements.btn) {
    elements.btn.disabled = true;
    elements.btn.textContent = "Predicting...";
  }

  try {
    const hasMLFields =
      !!(
        elements.sexEl &&
        elements.cpEl &&
        elements.trestbpsEl &&
        elements.cholEl &&
        elements.fbsEl &&
        elements.restecgEl &&
        elements.thalachEl &&
        elements.exangEl &&
        elements.oldpeakEl &&
        elements.slopeEl &&
        elements.caEl &&
        elements.thalEl
      );

    let data;

    if (hasMLFields) {
      const payload = buildPredictPayload(elements);

      for (const [k, v] of Object.entries(payload)) {
        if (!Number.isFinite(v)) {
          return renderError(`Please enter a valid number for ${k}.`);
        }
      }

      data = await predictRisk(payload);
    } else {
      data = await assessRisk(name, age);
    }

    renderRiskResult(data);
  } catch (err) {
    console.error(err);
    renderError("Unable to reach API. Make sure FastAPI is running on port 8000.");
  } finally {
    if (elements.btn) {
      elements.btn.disabled = false;
      elements.btn.textContent = "Predict Risk";
    }
  }
}