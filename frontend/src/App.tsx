import { Routes, Route } from "react-router-dom"
import Layout from "./layout/Layout"
import DashboardPage from "./pages/dashboard/DashboardPage"
import CashflowPage from "./pages/dashboard/CashflowPage"
import ProfitabilityPage from "./pages/dashboard/ProfitabilityPage"
import ReportPage from "./pages/dashboard/ReportPage"
import CompanyDashboardPage from "./pages/dashboard/CompanyDashboardPage"
import CoachDashboardPage from "./pages/dashboard/CoachDashboardPage"
import SurveyPage from "./pages/survey/SurveyPage"
import SurveyHistoryPage from "./pages/survey/SurveyHistoryPage"
import SurveyDetailPage from "./pages/survey/SurveyDetailPage"
import IngestPage from "./pages/ingest/IngestPage"
import SuropenPage from "./pages/suropen/SuropenPage"
import SuropenHistoryPage from "./pages/suropen/SuropenHistoryPage"
import ExportsPage from "./pages/exports/ExportsPage"
import CoachClientsPage from "./pages/coaching/CoachClientsPage"
import CoachClientDetailPage from "./pages/coaching/CoachClientDetailPage"
import PlaceholderPage from "./pages/PlaceholderPage"
import LoginPage from "./pages/auth/LoginPage"

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />

        <Route path="dashboard/cashflow" element={<CashflowPage />} />
        <Route path="dashboard/profitability" element={<ProfitabilityPage />} />
        <Route path="dashboard/report" element={<ReportPage />} />
        <Route path="dashboard/company" element={<CompanyDashboardPage />} />
        <Route path="dashboard/coach" element={<CoachDashboardPage />} />

        <Route path="survey" element={<SurveyPage />} />
        <Route path="survey/history" element={<SurveyHistoryPage />} />
        <Route path="survey/:batchId" element={<SurveyDetailPage />} />

        <Route path="ingest" element={<IngestPage />} />

        <Route path="suropen" element={<SuropenPage />} />
        <Route path="suropen/history" element={<SuropenHistoryPage />} />

        <Route path="exports" element={<ExportsPage />} />

        <Route path="coaching" element={<CoachClientsPage />} />
        <Route path="coaching/clients/:clientId" element={<CoachClientDetailPage />} />

        <Route
          path="chatbot"
          element={
            <PlaceholderPage
              title="Chatbot"
              template="chatbot/templates/chatbot/widget.html"
              description="Conversational assistant placeholder."
            />
          }
        />
        <Route path="accounts/login" element={<LoginPage />} />
        <Route
          path="accounts/register"
          element={
            <PlaceholderPage
              title="Register"
              template="templates/accounts/register.html"
              description="Account registration form."
            />
          }
        />
        <Route
          path="accounts/profile"
          element={
            <PlaceholderPage
              title="Profile"
              template="templates/accounts/profile.html"
              description="User profile view."
            />
          }
        />
        <Route
          path="accounts/profile/edit"
          element={
            <PlaceholderPage
              title="Edit profile"
              template="templates/accounts/profile_form.html"
              description="Profile edit form."
            />
          }
        />
        <Route
          path="coaching/profile"
          element={
            <PlaceholderPage
              title="Coach profile"
              template="coaching/templates/coaching/edit_coach.html"
              description="Coach profile editor."
            />
          }
        />
      </Route>
    </Routes>
  )
}
