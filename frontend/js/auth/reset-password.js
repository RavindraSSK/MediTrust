import {
  verifyResetCode,
  resetPassword,
} from "../services/api.js?v=20260418f";
import {
  renderPasswordRules,
  isPasswordValid,
  getPasswordValidationMessage,
} from "./password-rules.js?v=20260418f";
import { attachPasswordToggle } from "./password-toggle.js?v=20260418f";

const RESET_FLOW_KEY = "meditrust_reset_flow";
const form = document.getElementById("resetPasswordForm");
const message = document.getElementById("resetPasswordMessage");
const emailInput = document.getElementById("email");
const codeInput = document.getElementById("code");
const codeField = document.getElementById("resetCodeField");
const flowBanner = document.getElementById("resetFlowBanner");
const passwordInput = document.getElementById("newPassword");
const rulesBox = document.getElementById("passwordRules");
let verifiedResetContext = null;

attachPasswordToggle("newPassword", "toggleResetPassword", "resetEyeOpenIcon", "resetEyeClosedIcon");
attachPasswordToggle("confirmPassword", "toggleResetConfirmPassword", "resetConfirmEyeOpenIcon", "resetConfirmEyeClosedIcon");

passwordInput?.addEventListener("input", () => {
  renderPasswordRules(rulesBox, passwordInput.value);
});

renderPasswordRules(rulesBox, passwordInput?.value || "");

function setMessage(text = "") {
  if (!message) return;
  message.textContent = text;
}

function loadVerifiedResetContext() {
  const raw = sessionStorage.getItem(RESET_FLOW_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw);
    if (parsed?.verified && parsed?.email) {
      return parsed;
    }
  } catch (error) {
    sessionStorage.removeItem(RESET_FLOW_KEY);
  }

  return null;
}

function setFlowBanner(text, tone = "success") {
  if (!flowBanner) return;
  flowBanner.textContent = text;
  flowBanner.className = `flow-banner is-${tone}`;
  flowBanner.hidden = false;
}

function hideFlowBanner() {
  if (!flowBanner) return;
  flowBanner.hidden = true;
  flowBanner.textContent = "";
  flowBanner.className = "flow-banner";
}

function applyResetContext() {
  const params = new URLSearchParams(window.location.search);
  const emailFromQuery = params.get("email")?.trim().toLowerCase() || "";
  verifiedResetContext = loadVerifiedResetContext();

  if (verifiedResetContext?.email) {
    emailInput.value = verifiedResetContext.email;
    emailInput.readOnly = true;
    if (codeField) {
      codeField.hidden = true;
    }
    setFlowBanner("Verification complete. Create a new password to finish resetting your account.", "success");
    return;
  }

  if (emailFromQuery && emailInput && !emailInput.value) {
    emailInput.value = emailFromQuery;
  }

  hideFlowBanner();
}

applyResetContext();

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setMessage("");

  const email = emailInput.value.trim().toLowerCase();
  const code = codeInput.value.trim();
  const newPassword = document.getElementById("newPassword").value.trim();
  const confirmPassword = document.getElementById("confirmPassword").value.trim();
  const isVerifiedFlow = Boolean(verifiedResetContext?.verified && verifiedResetContext?.email === email);

  if (!email || !newPassword || !confirmPassword || (!isVerifiedFlow && !code)) {
    setMessage("Please complete all fields.");
    return;
  }

  if (newPassword !== confirmPassword) {
    setMessage("Passwords do not match.");
    return;
  }

  if (!isPasswordValid(newPassword)) {
    setMessage(getPasswordValidationMessage(newPassword));
    return;
  }

  try {
    if (!isVerifiedFlow) {
      const verify = await verifyResetCode(email, code);
      if (!verify.ok) {
        setMessage(verify.message || "Invalid reset code.");
        return;
      }
    }

    const out = await resetPassword(email, newPassword);
    if (!out.ok) {
      if (isVerifiedFlow && /verification required/i.test(out.message || "")) {
        sessionStorage.removeItem(RESET_FLOW_KEY);
        verifiedResetContext = null;
        if (codeField) {
          codeField.hidden = false;
        }
        setFlowBanner("Verification expired. Enter your 6-digit code again to continue.", "warning");
        setMessage("Verification expired. Please enter the latest reset code.");
        return;
      }

      setMessage(out.message || "Reset failed.");
      return;
    }

    sessionStorage.removeItem(RESET_FLOW_KEY);
    alert("Password reset successful. Please log in.");
    window.location.href = "index.html";
  } catch (error) {
    setMessage("Unable to reset password.");
  }
});
