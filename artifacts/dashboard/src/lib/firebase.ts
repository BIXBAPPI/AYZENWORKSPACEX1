import { initializeApp, getApps, FirebaseApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  FacebookAuthProvider,
  signInWithPopup,
  signInWithPhoneNumber,
  RecaptchaVerifier,
  Auth,
  UserCredential,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_WEB_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

export function isFirebaseConfigured(): boolean {
  return !!(firebaseConfig.apiKey && firebaseConfig.projectId);
}

export function getFirebaseApp(): FirebaseApp | null {
  if (!isFirebaseConfigured()) return null;
  if (!app) {
    app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  }
  return app;
}

export function getFirebaseAuth(): Auth | null {
  const fbApp = getFirebaseApp();
  if (!fbApp) return null;
  if (!auth) auth = getAuth(fbApp);
  return auth;
}

export async function signInWithGoogle(): Promise<{ idToken: string; email: string; name: string } | null> {
  const fbAuth = getFirebaseAuth();
  if (!fbAuth) throw new Error("Firebase not configured");
  const provider = new GoogleAuthProvider();
  provider.addScope("email");
  provider.addScope("profile");
  const result: UserCredential = await signInWithPopup(fbAuth, provider);
  const idToken = await result.user.getIdToken();
  return {
    idToken,
    email: result.user.email || "",
    name: result.user.displayName || "",
  };
}

export async function signInWithFacebook(): Promise<{ idToken: string; email: string; name: string } | null> {
  const fbAuth = getFirebaseAuth();
  if (!fbAuth) throw new Error("Firebase not configured");
  const provider = new FacebookAuthProvider();
  provider.addScope("email");
  const result: UserCredential = await signInWithPopup(fbAuth, provider);
  const idToken = await result.user.getIdToken();
  return {
    idToken,
    email: result.user.email || "",
    name: result.user.displayName || "",
  };
}

export async function setupRecaptcha(containerId: string): Promise<RecaptchaVerifier | null> {
  const fbAuth = getFirebaseAuth();
  if (!fbAuth) return null;
  return new RecaptchaVerifier(fbAuth, containerId, { size: "invisible" });
}

export async function exchangeFirebaseToken(idToken: string): Promise<boolean> {
  const res = await fetch("/api/v1/auth/firebase", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  return res.ok;
}
