import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { resetPassword, verifyResetCode } from "../api/endpoints.js";
import AuthShell from "../components/AuthShell.jsx";
import FormMessage from "../components/FormMessage.jsx";
import PasswordField from "../components/PasswordField.jsx";
import PasswordRulesList from "../components/PasswordRulesList.jsx";
import { getPasswordValidationMessage, isPasswordValid } from "../lib/passwordRules.js";
import { RESET_FLOW_KEY } from "./ForgotPasswordPage.jsx";

function loadVerifiedContext() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(RESET_FLOW_KEY) || "null");
    return parsed?.verified && parsed?.email ? parsed : null;
  } catch {
    sessionStorage.removeItem(RESET_FLOW_KEY);
    return null;
  }
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [context, setContext] = useState(() => loadVerifiedContext());
  const [email, setEmail] = useState(() => context?.email || params.get("email")?.trim().toLowerCase() || "");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [banner, setBanner] = useState(() =>
    context?.email
      ? { text: "Verification complete. Create a new password to finish resetting your account.", tone: "success" }
      : null
  );
  const [busy, setBusy] = useState(false);

  const isVerifiedFlow = Boolean(context?.verified && context?.email === email.trim().toLowerCase());

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    const target = email.trim().toLowerCase();
    if (!target || !newPassword || !confirmPassword || (!isVerifiedFlow && !code.trim())) {
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
    setBusy(true);
    try {
      if (!isVerifiedFlow) {
        const verify = await verifyResetCode(target, code.trim());
        if (!verify.ok) {
          setMessage(verify.message || "Invalid reset code.");
          return;
        }
      }
      const out = await resetPassword(target, newPassword);
      if (!out.ok) {
        if (isVerifiedFlow && /verification required/i.test(out.message || "")) {
          sessionStorage.removeItem(RESET_FLOW_KEY);
          setContext(null);
          setBanner({ text: "Verification expired. Enter your 6-digit code again to continue.", tone: "warning" });
          setMessage("Verification expired. Please enter the latest reset code.");
          return;
        }
        setMessage(out.message || "Reset failed.");
        return;
      }
      sessionStorage.removeItem(RESET_FLOW_KEY);
      window.alert("Password reset successful. Please log in.");
      navigate("/", { replace: true });
    } catch {
      setMessage("Unable to reset password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Reset Password" subtitle="Complete verification and create a new password for your account.">
      <form id="resetPasswordForm" className="login-form" noValidate onSubmit={handleSubmit}>
        {banner ? <div id="resetFlowBanner" className={`flow-banner is-${banner.tone}`}>{banner.text}</div> : null}
        <div className="field">
          <label htmlFor="email">Work Email</label>
          <div className="input-wrap">
            <input type="email" id="email" placeholder="Enter your work email" value={email} readOnly={Boolean(context?.email)} onChange={(event) => setEmail(event.target.value)} required />
          </div>
        </div>
        {!isVerifiedFlow ? (
          <div id="resetCodeField" className="field">
            <label htmlFor="code">Reset Code</label>
            <div className="input-wrap">
              <input type="text" id="code" placeholder="Enter 6-digit code" value={code} onChange={(event) => setCode(event.target.value)} required />
            </div>
          </div>
        ) : null}
        <PasswordField id="newPassword" label="New Password" placeholder="8 to 12 characters" value={newPassword} onChange={setNewPassword} autoComplete="new-password">
          <PasswordRulesList password={newPassword} />
        </PasswordField>
        <PasswordField id="confirmPassword" label="Confirm New Password" placeholder="Re-enter new password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
        <FormMessage id="resetPasswordMessage" text={message} />
        <button type="submit" className="signin-btn" disabled={busy}>
          {busy ? "Resetting..." : "Reset Password"}
        </button>
      </form>
      <div className="section-line" />
      <div className="secondary-row">
        <p>
          Back to account access?{" "}
          <Link to="/" className="text-link strong-link">
            Login
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
