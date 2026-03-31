import { requestPasswordReset } from "../services/api.js";

const form = document.getElementById("forgotPasswordForm");
const message = document.getElementById("forgotPasswordMessage");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  message.textContent = "";

  const email = document.getElementById("email").value.trim();

  if (!email) {
    message.textContent = "Please enter your work email.";
    return;
  }

  try {
    const data = await requestPasswordReset(email);
    message.textContent = data.message || "Reset code request submitted.";
  } catch (error) {
    message.textContent = "Unable to request reset code.";
  }
});