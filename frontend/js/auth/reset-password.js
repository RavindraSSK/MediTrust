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

const form = document.getElementById("resetPasswordForm");
const message = document.getElementById("resetPasswordMessage");
const passwordInput = document.getElementById("newPassword");
const rulesBox = document.getElementById("passwordRules");

attachPasswordToggle("newPassword", "toggleResetPassword", "resetEyeOpenIcon", "resetEyeClosedIcon");
attachPasswordToggle("confirmPassword", "toggleResetConfirmPassword", "resetConfirmEyeOpenIcon", "resetConfirmEyeClosedIcon");

passwordInput?.addEventListener("input", () => {
  renderPasswordRules(rulesBox, passwordInput.value);
});

renderPasswordRules(rulesBox, passwordInput?.value || "");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  message.textContent = "";

  const email = document.getElementById("email").value.trim();
  const code = document.getElementById("code").value.trim();
  const newPassword = document.getElementById("newPassword").value.trim();
  const confirmPassword = document.getElementById("confirmPassword").value.trim();

  if (!email || !code || !newPassword || !confirmPassword) {
    message.textContent = "Please complete all fields.";
    return;
  }

  if (newPassword !== confirmPassword) {
    message.textContent = "Passwords do not match.";
    return;
  }

  if (!isPasswordValid(newPassword)) {
    message.textContent = getPasswordValidationMessage(newPassword);
    return;
  }

  try {
    const verify = await verifyResetCode(email, code);
    if (!verify.ok) {
      message.textContent = verify.message || "Invalid reset code.";
      return;
    }

    const out = await resetPassword(email, newPassword);
    if (!out.ok) {
      message.textContent = out.message || "Reset failed.";
      return;
    }

    alert("Password reset successful. Please log in.");
    window.location.href = "index.html";
  } catch (error) {
    message.textContent = "Unable to reset password.";
  }
});
