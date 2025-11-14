import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
              AI Proctor
            </h1>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              Real-time Interview Monitoring System
            </p>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-12">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
              <div className="text-3xl mb-3">👁️</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Eye Gaze Tracking
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Monitors eye movement and detects when candidates look away from the screen
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
              <div className="text-3xl mb-3">👥</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Multiple Person Detection
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Alerts when more than one person appears in the video frame
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
              <div className="text-3xl mb-3">📱</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Phone Detection
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Identifies phones and other prohibited devices using AI object detection
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
              <div className="text-3xl mb-3">🔊</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
                Audio Analysis
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                Detects multiple voices and suspicious background audio
              </p>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/interview"
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-4 rounded-lg font-semibold text-lg text-center transition-colors shadow-lg"
            >
              Start Interview
            </Link>
            <Link
              href="/dashboard"
              className="bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-indigo-600 dark:text-indigo-400 px-8 py-4 rounded-lg font-semibold text-lg text-center transition-colors shadow-lg border-2 border-indigo-600 dark:border-indigo-400"
            >
              View Dashboard
            </Link>
          </div>

          {/* Tech Stack */}
          <div className="mt-16 text-center">
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-4">
              POWERED BY
            </h3>
            <div className="flex flex-wrap justify-center gap-6 text-sm text-gray-600 dark:text-gray-300">
              <span>MediaPipe</span>
              <span>•</span>
              <span>YOLO v8</span>
              <span>•</span>
              <span>FastAPI</span>
              <span>•</span>
              <span>Next.js 15</span>
              <span>•</span>
              <span>WebRTC</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
