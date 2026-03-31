import { changePassword } from "../services/api.js";
import { renderPasswordRules } from "./password-rules.js";

const form = document.getElementById("changePasswordForm");
const message = document.getElementById("changePasswordMessage");
const passwordInput = document.getElementById("newPassword");
const rulesBox = document.getElementById("passwordRules");

passwordInput?.addEventListener("input", () => {
  renderPasswordRules(rulesBox, passwordInput.value);
});

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