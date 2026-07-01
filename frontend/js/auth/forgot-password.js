import {
  requestPasswordReset,
  verifyResetCode,
} from "../services/api.js?v=20260701a";

const RESET_FLOW_KEY = "meditrust_reset_flow";
const form = document.getElementById("forgotPasswordForm");
const emailInput = document.getElementById("email");
const message = document.getElementById("forgotPasswordMessage");
const sendResetCodeBtn = document.getElementById("sendResetCodeBtn");
const otpStep = document.getElementById("otpStep");
const otpEmailPreview = document.getElementById("otpEmailPreview");
const otpMessage = document.getElementById("otpMessage");
const verifyResetCodeBtn = document.getElementById("verifyResetCodeBtn");
const resendResetCodeBtn = document.getElementById("resendResetCodeBtn");
const changeEmailBtn = document.getElementById("changeEmailBtn");
const otpGrid = document.getElementById("otpGrid");
const otpInputs = Array.from(document.querySelectorAll(".otp-input"));

function setMessage(target, text = "", tone = "") {
  if (!target) return;
  target.textContent = text;
  target.className = "form-message";
  if (target.id === "otpMessage") {
    target.classList.add("form-message-inline");
  }
  if (tone) {
    target.classList.add(`is-${tone}`);
  }
}

function normalizeEmail() {
  return emailInput?.value.trim().toLowerCase() || "";
}

function setOtpStepVisible(visible) {
  if (otpStep) {
    otpStep.hidden = !visible;
  }
  if (emailInput) {
    emailInput.readOnly = visible;
  }
}

function clearOtpInputs() {
  otpInputs.forEach((input) => {
    input.value = "";
  });
}

function focusOtpInput(index) {
  const input = otpInputs[index];
  if (input) {
    input.focus();
    input.select();
  }
}

function getOtpCode() {
  return otpInputs.map((input) => input.value).join("");
}

function setButtonBusy(button, busy, busyLabel, defaultLabel) {
  if (!button) return;
  button.disabled = busy;
  button.textContent = busy ? busyLabel : defaultLabel;
}

async function sendResetCode(email, options = {}) {
  const { resend = false } = options;
  setButtonBusy(sendResetCodeBtn, true, "Sending...", "Send Reset Code");
  if (resend) {
    setButtonBusy(resendResetCodeBtn, true, "Sending...", "Resend Code");
  }

  try {
    const data = await requestPasswordReset(email);
    if (!data?.ok) {
      setOtpStepVisible(false);
      clearOtpInputs();
      setMessage(
        message,
        data?.message || "No MediTrust account was found for this email.",
        "error"
      );
      setMessage(otpMessage);
      emailInput?.focus();
      emailInput?.select();
      return;
    }

    setMessage(
      message,
      data.message || "A 6-digit reset code has been sent to your email.",
      "success"
    );
    setMessage(
      otpMessage,
      resend
        ? "A new 6-digit code has been sent to your email."
        : "Enter the 6-digit code to continue.",
      resend ? "success" : "info"
    );
    if (otpEmailPreview) {
      otpEmailPreview.textContent = email;
    }
    setOtpStepVisible(true);
    clearOtpInputs();
    focusOtpInput(0);
  } catch (error) {
    setMessage(message, "Unable to request reset code.", "error");
  } finally {
    setButtonBusy(sendResetCodeBtn, false, "Sending...", "Send Reset Code");
    if (resend) {
      setButtonBusy(resendResetCodeBtn, false, "Sending...", "Resend Code");
    }
  }
}

otpInputs.forEach((input, index) => {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "").slice(-1);
    if (input.value && index < otpInputs.length - 1) {
      focusOtpInput(index + 1);
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Backspace" && !input.value && index > 0) {
      focusOtpInput(index - 1);
      return;
    }

    if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      focusOtpInput(index - 1);
      return;
    }

    if (event.key === "ArrowRight" && index < otpInputs.length - 1) {
      event.preventDefault();
      focusOtpInput(index + 1);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      verifyResetCodeBtn?.click();
    }
  });
});

otpGrid?.addEventListener("paste", (event) => {
  const pasted = event.clipboardData?.getData("text")?.replace(/\D/g, "").slice(0, 6) || "";
  if (!pasted) return;

  event.preventDefault();
  otpInputs.forEach((input, index) => {
    input.value = pasted[index] || "";
  });
  focusOtpInput(Math.min(pasted.length, otpInputs.length) - 1);
});

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setMessage(message);
  setMessage(otpMessage);

  const email = normalizeEmail();

  if (!email) {
    setMessage(message, "Please enter your work email.", "error");
    return;
  }

  sessionStorage.removeItem(RESET_FLOW_KEY);
  await sendResetCode(email);
});

verifyResetCodeBtn?.addEventListener("click", async () => {
  const email = normalizeEmail();
  const code = getOtpCode();

  setMessage(otpMessage);

  if (!email) {
    setMessage(message, "Please enter your work email.", "error");
    setOtpStepVisible(false);
    emailInput?.focus();
    return;
  }

  if (code.length !== 6) {
    setMessage(otpMessage, "Enter the full 6-digit verification code.", "error");
    focusOtpInput(0);
    return;
  }

  setButtonBusy(verifyResetCodeBtn, true, "Verifying...", "Continue");

  try {
    const result = await verifyResetCode(email, code);
    if (!result.ok) {
      setMessage(otpMessage, result.message || "Invalid or expired reset code.", "error");
      return;
    }

    sessionStorage.setItem(
      RESET_FLOW_KEY,
      JSON.stringify({
        email,
        verified: true,
        verifiedAt: Date.now(),
      })
    );
    setMessage(otpMessage, "Code verified. Redirecting to password reset...", "success");
    window.location.href = `reset-password.html?email=${encodeURIComponent(email)}`;
  } catch (error) {
    setMessage(otpMessage, "Unable to verify reset code.", "error");
  } finally {
    setButtonBusy(verifyResetCodeBtn, false, "Verifying...", "Continue");
  }
});

resendResetCodeBtn?.addEventListener("click", async () => {
  const email = normalizeEmail();
  if (!email) {
    setMessage(message, "Please enter your work email.", "error");
    emailInput?.focus();
    return;
  }
  await sendResetCode(email, { resend: true });
});

changeEmailBtn?.addEventListener("click", () => {
  sessionStorage.removeItem(RESET_FLOW_KEY);
  setOtpStepVisible(false);
  clearOtpInputs();
  setMessage(message);
  setMessage(otpMessage);
  emailInput?.focus();
  emailInput?.select();
});
