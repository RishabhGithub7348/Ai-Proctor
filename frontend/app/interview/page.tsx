"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  useCreateSession,
  useEndSession,
  useWebSocket,
  useProctoringStatus,
} from "@/lib/hooks";
import { Alert } from "@/lib/api/types";

export default function InterviewPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [candidateName, setCandidateName] = useState("");
  const [showStartForm, setShowStartForm] = useState(true);
  const [tabSwitchCount, setTabSwitchCount] = useState(0);

  // API Hooks
  const createSessionMutation = useCreateSession();
  const endSessionMutation = useEndSession();

  // WebSocket Hook
  const {
    isConnected,
    sendBlob,
    disconnect: disconnectWs,
  } = useWebSocket(sessionId, {
    onAlert: (newAlerts) => {
      setAlerts((prev) => [...newAlerts, ...prev].slice(0, 20));
    },
    onMessage: (data) => {
      console.log("Received data:", data);

      // Handle proctoring results
      if (data.type === "proctoring_result" && data.data) {
        const result = data.data;

        // Add alerts if any
        if (result.alerts && result.alerts.length > 0) {
          setAlerts((prev) => [...result.alerts, ...prev].slice(0, 20));
        }
      }
    },
  });

  // Proctoring Status Hook (polling every 5 seconds when session is active)
  const { data: proctoringStatus } = useProctoringStatus(sessionId, {
    enabled: !!sessionId && isStreaming,
    refetchInterval: 5000,
  });

  // Start video stream
  const startVideo = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: true,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsStreaming(true);
      }
    } catch (error) {
      console.error("Error accessing camera:", error);
      alert("Failed to access camera. Please grant camera permissions.");
    }
  };

  // Stop video stream
  const stopVideo = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
      setIsStreaming(false);
    }

    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  };

  // Start session
  const handleStartSession = async () => {
    if (!candidateName.trim()) {
      alert("Please enter your name");
      return;
    }

    try {
      // Create session via API
      const session = await createSessionMutation.mutateAsync({
        candidate_name: candidateName,
        interview_type: "technical",
        duration_minutes: 60,
      });

      setSessionId(session.session_id);
      setShowStartForm(false);

      // Start video
      await startVideo();
    } catch (error) {
      console.error("Failed to start session:", error);
      alert("Failed to start session. Please try again.");
    }
  };

  // End session
  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      // End session via API
      await endSessionMutation.mutateAsync(sessionId);

      // Stop video and disconnect WebSocket
      stopVideo();
      disconnectWs();

      // Reset state
      setSessionId(null);
      setAlerts([]);
      setShowStartForm(true);
      setCandidateName("");
    } catch (error) {
      console.error("Failed to end session:", error);
      alert("Failed to end session properly.");
    }
  };

  // Send video frames to backend
  useEffect(() => {
    if (!isStreaming || !isConnected || !videoRef.current || !canvasRef.current) {
      return;
    }

    frameIntervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (video && canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0);

          // Convert to blob and send via WebSocket
          canvas.toBlob((blob) => {
            if (blob) {
              sendBlob(blob);
            }
          }, "image/jpeg", 0.8);
        }
      }
    }, 1000); // Send frame every second

    return () => {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    };
  }, [isStreaming, isConnected, sendBlob]);

  // Tab switching detection
  useEffect(() => {
    if (!sessionId || !isStreaming) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // User switched tab or minimized window
        const switchTime = new Date().toISOString();
        setTabSwitchCount((prev) => prev + 1);

        // Create alert
        const tabSwitchAlert: Alert = {
          alert_id: `tab_switch_${Date.now()}`,
          type: "tab_switch",
          severity: "medium",
          message: `Candidate switched tab/window at ${new Date(switchTime).toLocaleTimeString()}`,
          timestamp: switchTime,
          requires_attention: true,
        };

        setAlerts((prev) => [tabSwitchAlert, ...prev].slice(0, 20));

        console.log("⚠️ Tab switch detected:", switchTime);
      } else {
        // User returned to tab
        console.log("✅ User returned to interview tab");
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [sessionId, isStreaming]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopVideo();
      disconnectWs();
    };
  }, [disconnectWs]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-100 border-red-500 text-red-900";
      case "high":
        return "bg-orange-100 border-orange-500 text-orange-900";
      case "medium":
        return "bg-yellow-100 border-yellow-500 text-yellow-900";
      default:
        return "bg-blue-100 border-blue-500 text-blue-900";
    }
  };

  // Show start form if no session
  if (showStartForm) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 text-center">
            Start Interview Session
          </h1>

          <div className="space-y-4">
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Candidate Name
              </label>
              <input
                type="text"
                id="name"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                placeholder="Enter your name"
              />
            </div>

            <button
              onClick={handleStartSession}
              disabled={createSessionMutation.isPending}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
            >
              {createSessionMutation.isPending
                ? "Starting..."
                : "Start Interview"}
            </button>

            <Link
              href="/"
              className="block text-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              AI Proctor - Interview Session
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-1">
              {candidateName} • {sessionId}
            </p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-900 dark:text-white transition-colors"
          >
            Back to Home
          </Link>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Video Feed */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Video Feed
                </h2>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
                    }`}
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    {isConnected ? "Connected" : "Disconnected"}
                  </span>
                </div>
              </div>

              {/* Video Element */}
              <div className="relative bg-black rounded-lg overflow-hidden aspect-video">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                {!isStreaming && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <p className="text-white text-lg">Camera not active</p>
                  </div>
                )}
              </div>

              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} className="hidden" />

              {/* Controls */}
              <div className="mt-6 flex gap-4">
                <button
                  onClick={handleEndSession}
                  disabled={endSessionMutation.isPending}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                >
                  {endSessionMutation.isPending
                    ? "Ending..."
                    : "End Interview"}
                </button>
              </div>
            </div>

            {/* Stats */}
            <div className="mt-6 grid grid-cols-5 gap-4">
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {alerts.length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Total Alerts
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {alerts.filter((a) => a.severity === "critical").length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Critical
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {alerts.filter((a) => a.severity === "high").length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  High
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-2xl font-bold text-orange-600">
                  {tabSwitchCount}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Tab Switches
                </div>
              </div>
              <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
                <div className="text-2xl font-bold text-green-600">
                  {isStreaming ? "Active" : "Inactive"}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Status
                </div>
              </div>
            </div>
          </div>

          {/* Alerts Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Alerts
              </h2>

              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {alerts.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-8">
                    No alerts yet
                  </p>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.alert_id}
                      className={`p-4 rounded-lg border-l-4 ${getSeverityColor(
                        alert.severity
                      )}`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-semibold text-sm uppercase">
                          {alert.type.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm">{alert.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Detection Status */}
            <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Active Monitoring
              </h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Eye Gaze Tracking
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Face Detection
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Object Detection
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Audio Analysis
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isStreaming ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Tab Switch Detection
                  </span>
                </div>
              </div>
            </div>

            {/* Current Status */}
            {proctoringStatus && (
              <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Current Status
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Active:
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {proctoringStatus.is_active ? "Yes" : "No"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">
                      Violations:
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {proctoringStatus.current_violations.length}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
