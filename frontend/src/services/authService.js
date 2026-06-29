// --- Auth Service ---
// Temporary local-storage backed "user database" so people can register,
// log back in, and have their cold-start data persist between sessions.
//
// The public functions below (registerUser, loginUser, saveColdStartRatings,
// getCurrentUser) are the contract the rest of the app depends on. Swapping
// this out for a real backend later just means re-implementing these
// functions to call an API instead of touching localStorage.

const USERS_KEY = 'rubeer_users';

const readUsers = () => {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY)) || {};
  } catch {
    return {};
  }
};

const writeUsers = (users) => {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
};

const toPublicUser = (email, record) => ({
  email,
  userId: email,
  username: record.username || email,
  needsColdStart: !record.coldStartCompleted,
  ratings: record.ratings || {},
});

export const registerUser = (username, email, password) => {
  const normalizedEmail = email.trim().toLowerCase();
  const users = readUsers();

  if (users[normalizedEmail]) {
    return { success: false, error: 'An account with this email already exists.' };
  }

  users[normalizedEmail] = {
    username: username.trim(),
    password,
    coldStartCompleted: false,
    ratings: {},
  };
  writeUsers(users);

  return { success: true, user: toPublicUser(normalizedEmail, users[normalizedEmail]) };
};

export const loginUser = (email, password) => {
  const normalizedEmail = email.trim().toLowerCase();
  const users = readUsers();
  const record = users[normalizedEmail];

  if (!record || record.password !== password) {
    return { success: false, error: 'Invalid email or password.' };
  }

  return { success: true, user: toPublicUser(normalizedEmail, record) };
};

export const getUserRecord = (email) => {
  const users = readUsers();
  return users[email.trim().toLowerCase()] || null;
};

export const updateDisplayName = (email, newName) => {
  const trimmed = newName.trim();
  if (!trimmed) return { success: false, error: 'Display name cannot be empty.' };
  const users = readUsers();
  const record = users[email.trim().toLowerCase()];
  if (!record) return { success: false, error: 'User not found.' };
  record.username = trimmed;
  writeUsers(users);
  return { success: true };
};

export const updatePassword = (email, currentPw, newPw) => {
  const users = readUsers();
  const record = users[email.trim().toLowerCase()];
  if (!record || record.password !== currentPw)
    return { success: false, error: 'Current password is incorrect.' };
  if (newPw.length < 6)
    return { success: false, error: 'New password must be at least 6 characters.' };
  record.password = newPw;
  writeUsers(users);
  return { success: true };
};

export const saveRating = (email, beerId, rating) => {
  const normalizedEmail = email.trim().toLowerCase();
  const users = readUsers();
  const record = users[normalizedEmail];
  if (!record) return;
  record.ratings = { ...record.ratings, [String(beerId)]: rating };
  writeUsers(users);
};

export const saveColdStartRatings = (email, ratings) => {
  const normalizedEmail = email.trim().toLowerCase();
  const users = readUsers();
  const record = users[normalizedEmail];

  if (!record) return;

  record.ratings = { ...record.ratings, ...ratings };
  record.coldStartCompleted = true;
  writeUsers(users);
};
