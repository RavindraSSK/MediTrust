import { PASSWORD_RULE_ITEMS, getPasswordValidation } from "../lib/passwordRules.js";

export default function PasswordRulesList({ password }) {
  const rules = getPasswordValidation(password || "");
  return (
    <div className="password-rules">
      <ul className="rules-list">
        {PASSWORD_RULE_ITEMS.map(([key, label]) => (
          <li key={key} className={rules[key] ? "rule-ok" : "rule-pending"}>
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
