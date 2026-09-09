import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { requestPasswordReset, verifyResetCode } from "../api/endpoints.js";
import AuthShell from "../components/AuthShell.jsx";
import FormMessage from "../components/FormMessage.jsx";

export const RESET_FLOW_KEY = "meditrust_reset_flow";
const EMPTY_CODE = ["", "", "", "", "", ""];

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState({ text: "", tone: "" });
  const [otpMessage, setOtpMessage] = useState({ text: "", tone: "" });
  const [otpVisible, setOtpVisible] = useState(false);
  const [digits, setDigits] = useState(EMPTY_CODE);
  const [sending, setSending] = useState(false);
  const [resending, setResending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const inputs = useRef([]);

  const normalizedEmail = () => email.trim().toLowerCase();

  const focusDigit = (index) => {
    const node = inputs.current[index];
    if (node) {
      node.focus();
      node.select();
    }
  };

  const sendCode = async ({ resend = false } = {}) => {
    const target = normalizedEmail();
    if (!target) {
      setMessage({ text: "Please enter your work email.", tone: "error" });
      return;
    }
    resend ? setResending(true) : setSending(true);
    try {
      const data = await requestPasswordReset(target);
      if (!data?.ok) {
        setOtpVisible(false);
        setDigits(EMPTY_CODE);
        setMessage({ text: data?.message || "No MediTrust account was found for this email.", tone: "error" });
        setOtpMessage({ text: "", tone: "" });
        return;
      }
      setMessage({ text: data.message || "A 6-digit reset code has been sent to your email.", tone: "success" });
      setOtpMessage({
        text: resend ? "A new 6-digit code has been sent to your email." : "Enter the 6-digit code to continue.",
        tone: resend ? "success" : "info",
      });
      setOtpVisible(true);
      setDigits(EMPTY_CODE);
      setTimeout(() => focusDigit(0), 0);
    } catch {
      setMessage({ text: "Unable to request reset code.", tone: "error" });
    } finally {
      setSending(false);
      setResending(false);
    }
  };

  const handleDigitChange = (index, value) => {
    const digit = value.replace(/\D/g, "").slice(-1);
    setDigits((current) => current.map((item, i) => (i === index ? digit : item)));
    if (digit && index < 5) focusDigit(index + 1);
  };

  const handleDigitKey = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      focusDigit(index - 1);
    } else if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      focusDigit(index - 1);
    } else if (event.key === "ArrowRight" && index < 5) {
      event.preventDefault();
      focusDigit(index + 1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      verify();
    }
  };

  const handlePaste = (event) => {
    const pasted = (event.clipboardData?.getData("text") || "").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    event.preventDefault();
    setDigits(EMPTY_CODE.map((_, i) => pasted[i] || ""));
    focusDigit(Math.min(pasted.length, 6) - 1);
  };

  const verify = async () => {
    const target = normalizedEmail();
    const code = digits.join("");
    setOtpMessage({ text: "", tone: "" });
    if (!target) {
      setMessage({ text: "Please enter your work email.", tone: "error" });
      setOtpVisible(false);
      return;
    }
    if (code.length !== 6) {
      setOtpMessage({ text: "Enter the full 6-digit verification code.", tone: "error" });
      focusDigit(0);
      return;
    }
    setVerifying(true);
    try {
      const result = await verifyResetCode(target, code);
      if (!result.ok) {
        setOtpMessage({ text: result.message || "Invalid or expired reset code.", tone: "error" });
        return;
      }
      sessionStorage.setItem(RESET_FLOW_KEY, JSON.stringify({ email: target, verified: true }));
      setOtpMessage({ text: "Code verified. Redirecting to password reset...", tone: "success" });
      navigate(`/reset-password?email=${encodeURIComponent(target)}`);
    } catch {
      setOtpMessage({ text: "Unable to verify reset code.", tone: "error" });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <AuthShell title="Forgot Password" subtitle="Enter your work email to receive a 6-digit password reset code.">
      <form
        id="forgotPasswordForm"
        className="login-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          setMessage({ text: "", tone: "" });
          setOtpMessage({ text: "", tone: "" });
          sessionStorage.removeItem(RESET_FLOW_KEY);
          sendCode();
        }}
      >
        <div className="field">
          <label htmlFor="email">Work Email</label>
          <div className="input-wrap">
            <input type="email" id="email" placeholder="Enter your work email" value={email} readOnly={otpVisible} onChange={(event) => setEmail(event.target.value)} required />
          </div>
        </div>
        <FormMessage id="forgotPasswordMessage" text={message.text} tone={message.tone} />
        <button id="sendResetCodeBtn" type="submit" className="signin-btn" disabled={sending}>
          {sending ? "Sending..." : "Send Reset Code"}
        </button>
      </form>

      {otpVisible ? (
        <section id="otpStep" className="otp-step" aria-live="polite">
          <div className="step-card">
            <div className="step-heading">
              <h3 className="step-title">Enter Verification Code</h3>
              <p className="step-subtitle">
                Enter the 6-digit code sent to <strong>{normalizedEmail()}</strong> to continue.
              </p>
            </div>
            <FormMessage id="otpMessage" text={otpMessage.text} tone={otpMessage.tone} inline />
            <div id="otpGrid" className="otp-grid" role="group" aria-label="6-digit reset code" onPaste={handlePaste}>
              {digits.map((digit, index) => (
                <input
                  key={index}
                  ref={(node) => {
                    inputs.current[index] = node;
                  }}
                  className="otp-input"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={1}
                  aria-label={`Digit ${index + 1}`}
                  value={digit}
                  onChange={(event) => handleDigitChange(index, event.target.value)}
                  onKeyDown={(event) => handleDigitKey(index, event)}
                />
              ))}
            </div>
            <div className="otp-actions">
              <button id="verifyResetCodeBtn" type="button" className="signin-btn" onClick={verify} disabled={verifying}>
                {verifying ? "Verifying..." : "Continue"}
              </button>
              <button id="resendResetCodeBtn" type="button" className="secondary-btn" onClick={() => sendCode({ resend: true })} disabled={resending}>
                {resending ? "Sending..." : "Resend Code"}
              </button>
            </div>
            <div className="otp-footer-row">
              <span className="step-note">Use the latest code from your email inbox.</span>
              <button
                id="changeEmailBtn"
                type="button"
                className="inline-btn"
                onClick={() => {
                  sessionStorage.removeItem(RESET_FLOW_KEY);
                  setOtpVisible(false);
                  setDigits(EMPTY_CODE);
                  setMessage({ text: "", tone: "" });
                  setOtpMessage({ text: "", tone: "" });
                }}
              >
                Use a different email
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <div className="section-line" />
      <div className="secondary-row">
        <p>
          Already have your code?{" "}
          <Link to="/reset-password" className="text-link strong-link">
            Reset Password
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
