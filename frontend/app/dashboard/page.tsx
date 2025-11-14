import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <Link
            href="/"
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg text-gray-900 dark:text-white transition-colors"
          >
            Back to Home
          </Link>
        </div>

        {/* Coming Soon */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
            Dashboard Coming Soon
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-8">
            The dashboard will display session history, analytics, and detailed reports.
          </p>
          <Link
            href="/interview"
            className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
          >
            Start an Interview
          </Link>
        </div>
      </div>
    </div>
  );
}
