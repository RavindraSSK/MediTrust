export function getPasswordValidation(password) {
  return {
    minLength: password.length >= 8,
    maxLength: password.length <= 12,
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
    hasSpecial: /[^A-Za-z0-9]/.test(password),
  };
}

export function isPasswordValid(password) {
  const rules = getPasswordValidation(password);
  return Object.values(rules).every(Boolean);
}

export function getPasswordValidationMessage(password) {
  const rules = getPasswordValidation(password);

  if (!rules.minLength || !rules.maxLength) {
    return "Password must be 8 to 12 characters long.";
  }
  if (!rules.hasUpper) {
    return "Password must include at least one uppercase letter.";
  }
  if (!rules.hasLower) {
    return "Password must include at least one lowercase letter.";
  }
  if (!rules.hasNumber) {
    return "Password must include at least one number.";
  }
  if (!rules.hasSpecial) {
    return "Password must include at least one special character.";
  }

  return "";
}

export function renderPasswordRules(container, password) {
  if (!container) return;

  const rules = getPasswordValidation(password);

  const items = [
    { label: "Minimum 8 characters", ok: rules.minLength },
    { label: "Maximum 12 characters", ok: rules.maxLength },
    { label: "At least one uppercase letter", ok: rules.hasUpper },
    { label: "At least one lowercase letter", ok: rules.hasLower },
    { label: "At least one number", ok: rules.hasNumber },
    { label: "At least one special character", ok: rules.hasSpecial },
  ];

  container.innerHTML = `
    <ul class="rules-list">
      ${items.map(item => `
        <li class="${item.ok ? "rule-ok" : "rule-pending"}">
          ${item.label}
        </li>
      `).join("")}
    </ul>
  `;
}
