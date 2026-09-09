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

export const PASSWORD_RULE_ITEMS = [
  ["minLength", "Minimum 8 characters"],
  ["maxLength", "Maximum 12 characters"],
  ["hasUpper", "At least one uppercase letter"],
  ["hasLower", "At least one lowercase letter"],
  ["hasNumber", "At least one number"],
  ["hasSpecial", "At least one special character"],
];

export function isPasswordValid(password) {
  return Object.values(getPasswordValidation(password)).every(Boolean);
}

export function getPasswordValidationMessage(password) {
  const rules = getPasswordValidation(password);
  if (!rules.minLength || !rules.maxLength) return "Password must be 8 to 12 characters long.";
  if (!rules.hasUpper) return "Password must include at least one uppercase letter.";
  if (!rules.hasLower) return "Password must include at least one lowercase letter.";
  if (!rules.hasNumber) return "Password must include at least one number.";
  if (!rules.hasSpecial) return "Password must include at least one special character.";
  return "";
}
