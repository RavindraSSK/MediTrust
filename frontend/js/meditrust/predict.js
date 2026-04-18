import { safeNumber } from "../utils.js?v=20260418f";
import { predictRisk, assessRisk } from "../services/api.js?v=20260418f";
import { renderError, clearError, renderRiskResult } from "./render.js?v=20260418f";
import { buildPredictPayload } from "./form.js?v=20260418f";

export async function handlePrediction(elements, currentUser = null) {
  clearError();

  const firstName = (elements.firstNameEl?.value || "").trim();
  const lastName = (elements.lastNameEl?.value || "").trim();
  const name = `${firstName} ${lastName}`.trim();
  const age = safeNumber(elements.ageEl?.value);

  if (!firstName || !lastName) {
    return renderError("Please enter the patient's first and last name.");
  }
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
        if (k === "first_name" || k === "last_name") {
          if (!String(v || "").trim()) {
            return renderError(`Please enter a valid value for ${k.replace("_", " ")}.`);
          }
          continue;
        }

        if (!Number.isFinite(v)) {
          return renderError(`Please enter a valid number for ${k}.`);
        }
      }

      data = await predictRisk(payload);
    } else {
      data = await assessRisk(firstName, lastName, age);
    }

    data.patient_name = name;
    data.current_role = currentUser?.role || "Clinician";
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
