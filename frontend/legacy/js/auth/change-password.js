import { changePassword } from "../services/api.js?v=20260701a";
import {
  renderPasswordRules,
  isPasswordValid,
  getPasswordValidationMessage,
} from "./password-rules.js?v=20260701a";
import { attachPasswordToggle } from "./password-toggle.js?v=20260701a";

const form = document.getElementById("changePasswordForm");
const message = document.getElementById("changePasswordMessage");
const passwordInput = document.getElementById("newPassword");
const rulesBox = document.getElementById("passwordRules");

attachPasswordToggle("currentPassword", "toggleCurrentPassword", "currentEyeOpenIcon", "currentEyeClosedIcon");
attachPasswordToggle("newPassword", "toggleChangePassword", "changeEyeOpenIcon", "changeEyeClosedIcon");
attachPasswordToggle("confirmPassword", "toggleChangeConfirmPassword", "changeConfirmEyeOpenIcon", "changeConfirmEyeClosedIcon");

passwordInput?.addEventListener("input", () => {
  renderPasswordRules(rulesBox, passwordInput.value);
});

renderPasswordRules(rulesBox, passwordInput?.value || "");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  message.textContent = "";

  const email = document.getElementById("email").value.trim();
  const currentPassword = document.getElementById("currentPassword").value.trim();
  const newPassword = document.getElementById("newPassword").value.trim();
  const confirmPassword = document.getElementById("confirmPassword").value.trim();

  if (!email || !currentPassword || !newPassword || !confirmPassword) {
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
    const out = await changePassword(email, currentPassword, newPassword);
    if (!out.ok) {
      message.textContent = out.message || "Password change failed.";
      return;
    }

    alert("Password changed successfully.");
    window.location.href = "index.html";
  } catch (error) {
    message.textContent = "Unable to change password.";
  }
});
