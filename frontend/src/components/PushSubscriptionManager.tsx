import React, { useEffect, useState } from "react";
import { Bell, BellOff, Loader2 } from "lucide-react";
import { api } from "../api/client";

const VAPID_PUBLIC_KEY_URL = "/notifications/vapid-public-key";
const SUBSCRIBE_URL = "/notifications/subscribe";

// Vite: service worker should be in /public/sw.js
const SW_URL = "/sw.js";

export const PushSubscriptionManager: React.FC = () => {
    const [isSubscribed, setIsSubscribed] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    useEffect(() => {
        checkSubscription().catch((e) => {
            console.error("checkSubscription failed:", e);
            setError("Failed to initialize push subscription state.");
        });
    }, []);

    const urlBase64ToUint8Array = (base64StringRaw: string) => {
        // base64url -> base64
        const base64String = base64StringRaw.trim();
        const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
        const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    };

    const sanitizePublicKey = (key: unknown) => {
        if (typeof key !== "string") return "";
        return key
            .trim()
            .replace(/^VAPID_PUBLIC_KEY\s*=\s*/i, "")
            .replace(/^"+|"+$/g, "")
            .replace(/^'+|'+$/g, "")
            .replace(/\s+/g, "")                 // <-- прибираємо ВСІ пробіли/переноси
            .replace(/[^A-Za-z0-9\-_]/g, "");    // <-- прибираємо будь-які не-base64url символи
    };


    const ensureServiceWorker = async (): Promise<ServiceWorkerRegistration> => {
        if (!("serviceWorker" in navigator)) {
            throw new Error("Service Worker not supported");
        }

        // If already registered, use it; otherwise register.
        const existing = await navigator.serviceWorker.getRegistration();
        if (existing) return existing;

        const reg = await navigator.serviceWorker.register(SW_URL);
        await navigator.serviceWorker.ready;
        return reg;
    };

    const checkSubscription = async () => {
        if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
            setError("Push notifications not supported");
            return;
        }

        const registration = await ensureServiceWorker();
        const subscription = await registration.pushManager.getSubscription();
        setIsSubscribed(!!subscription);
    };

    const subscribe = async () => {
        setLoading(true);
        setError("");
        setMessage("");

        try {
            if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
                throw new Error("Push notifications not supported");
            }

            const registration = await ensureServiceWorker();

            // Get VAPID public key from backend
            const resKey = await api.get(VAPID_PUBLIC_KEY_URL);
            const publicKey = sanitizePublicKey(resKey?.data?.publicKey);

            if (!publicKey) {
                throw new Error("VAPID public key is missing/empty after sanitize.");
            }

            const convertedVapidKey = urlBase64ToUint8Array(publicKey);

            // Діагностика (важливо)
            console.log("publicKey string length:", publicKey.length);
            console.log("publicKey bytes length:", convertedVapidKey.length);
            console.log("publicKey first byte:", convertedVapidKey[0]);

            if (convertedVapidKey.length !== 65 || convertedVapidKey[0] !== 4) {
                throw new Error(
                    `Invalid VAPID public key. Expected 65 bytes starting with 0x04. ` +
                    `Got length=${convertedVapidKey.length}, firstByte=${convertedVapidKey[0]}.`
                );
            }


            // Optional: If already subscribed, avoid duplicate subscribe calls
            const existingSub = await registration.pushManager.getSubscription();
            if (existingSub) {
                // If you prefer, re-send existing to backend:
                await api.post(SUBSCRIBE_URL, existingSub.toJSON());
                setIsSubscribed(true);
                setMessage("Notifications already enabled (subscription refreshed).");
                return;
            }

            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: convertedVapidKey,
            });

            await api.post(SUBSCRIBE_URL, subscription.toJSON());

            setIsSubscribed(true);
            setMessage("Notifications enabled!");
        } catch (err: any) {
            console.error("Subscription failed", err);
            setError("Failed to subscribe: " + (err?.message || String(err)));
        } finally {
            setLoading(false);
        }
    };

    const unsubscribe = async () => {
        setLoading(true);
        setError("");
        setMessage("");

        try {
            const registration = await navigator.serviceWorker.getRegistration();
            if (!registration) {
                setIsSubscribed(false);
                setMessage("Notifications disabled.");
                return;
            }

            const subscription = await registration.pushManager.getSubscription();
            if (subscription) {
                await subscription.unsubscribe();
            }

            setIsSubscribed(false);
            setMessage("Notifications disabled.");
        } catch (err: any) {
            console.error("Unsubscribe failed", err);
            setError("Failed to unsubscribe: " + (err?.message || String(err)));
        } finally {
            setLoading(false);
        }
    };

    if (error === "Push notifications not supported") {
        return null;
    }

    return (
        <div className="bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20 mt-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                        <Bell size={22} />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">Сповіщення</p>
                        <h2 className="text-lg font-semibold text-white">Push-сповіщення</h2>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <p className="text-sm text-gray-400">
                    Отримуйте сповіщення про нові дайджести та важливі листи.
                </p>

                {message && <p className="text-sm text-green-400">{message}</p>}
                {error && <p className="text-sm text-red-400">{error}</p>}

                <button
                    onClick={isSubscribed ? unsubscribe : subscribe}
                    disabled={loading}
                    className={`flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium transition-all shadow-lg w-full sm:w-auto mt-2
            ${isSubscribed
                            ? "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 shadow-red-900/10"
                            : "bg-primary-600 hover:bg-primary-500 text-white shadow-primary-900/20"
                        }`}
                >
                    {loading ? (
                        <Loader2 className="animate-spin" size={18} />
                    ) : isSubscribed ? (
                        <BellOff size={18} />
                    ) : (
                        <Bell size={18} />
                    )}
                    <span>{isSubscribed ? "Вимкнути сповіщення" : "Увімкнути сповіщення"}</span>
                </button>
            </div>
        </div>
    );
};
