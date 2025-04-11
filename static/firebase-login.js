// firebase-login.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.0/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/11.6.0/firebase-auth.js";

// Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyDuEwrxCqcSbf_Js7cxl4XYX3Jq3XZuDZ8",
  authDomain: "task-manager-app-881dd.firebaseapp.com",
  projectId: "task-manager-app-881dd",
  storageBucket: "task-manager-app-881dd.firebasestorage.app",
  messagingSenderId: "686537932743",
  appId: "1:686537932743:web:7d77e79446e9c5dbf2a3e2"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Attach login/signup/logout to window (global scope)
window.firebaseLogin = (email, password) => {
  return signInWithEmailAndPassword(auth, email, password);
};

window.firebaseSignup = (email, password) => {
  return createUserWithEmailAndPassword(auth, email, password);
};

window.firebaseLogout = () => {
  return signOut(auth);
};

window.getCurrentUser = () => {
  return auth.currentUser;
};
