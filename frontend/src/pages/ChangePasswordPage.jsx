import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { changePassword } from "../api/endpoints.js";
import { useAuth } from "../auth/AuthContext.jsx";
import AuthShell from "../components/AuthShell.jsx";
import FormMessage from "../components/FormMessage.jsx";
import PasswordField from "../components/PasswordField.jsx";
import PasswordRulesList from "../components/PasswordRulesList.jsx";
import { errorMessage } from "../lib/format.js";
import { getPasswordValidationMessage, isPasswordValid } from "../lib/passwordRules.js";

export default function ChangePasswordPage() {
  const { user, dashboardPath } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    if (!currentPassword || !newPassword || !confirmPassword) {
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
      const out = await changePassword(currentPassword, newPassword);
      if (!out.ok) {
        setMessage(out.message || "Password change failed.");
        return;
      }
      window.alert("Password changed successfully.");
      navigate(dashboardPath, { replace: true });
    } catch (error) {
      setMessage(errorMessage(error, "Unable to change password."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Change Password" subtitle="Update the password for your current clinician account.">
      <form id="changePasswordForm" className="login-form" noValidate onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="email">Work Email</label>
          <div className="input-wrap">
            <input type="email" id="email" value={user?.email || ""} readOnly />
          </div>
        </div>
        <PasswordField id="currentPassword" label="Current Password" placeholder="Enter current password" value={currentPassword} onChange={setCurrentPassword} />
        <PasswordField id="newPassword" label="New Password" placeholder="8 to 12 characters" value={newPassword} onChange={setNewPassword} autoComplete="new-password">
          <PasswordRulesList password={newPassword} />
        </PasswordField>
        <PasswordField id="confirmPassword" label="Confirm New Password" placeholder="Re-enter new password" value={confirmPassword} onChange={setConfirmPassword} autoComplete="new-password" />
        <FormMessage id="changePasswordMessage" text={message} />
        <button type="submit" className="signin-btn" disabled={busy}>
          {busy ? "Saving..." : "Change Password"}
        </button>
      </form>
      <div className="section-line" />
      <div className="secondary-row">
        <p>
          <Link to={dashboardPath} className="text-link strong-link">
            Back to dashboard
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
