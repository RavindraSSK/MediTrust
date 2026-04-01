import {
  verifyResetCode,
  resetPassword,
} from "../services/api.js";

const form = document.getElementById("resetPasswordForm");
const message = document.getElementById("resetPasswordMessage");

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