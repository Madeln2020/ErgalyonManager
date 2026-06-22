// @ts-nocheck
"use client";

import React, { useEffect, useState } from "react";
import DashboardLayout from "../DashboardLayout";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Tabs, Button, Table, Select, Loader, Badge } from "@mantine/core";

type CostUpdate = {
  id: string;
  product_name: string;
  supplier_name: string;
  old_cost: number;
  new_cost: number;
  source: string;
  created_at: string;
  status: "pending" | "approved" | "rejected";
  reason?: string;
};

type ExportJob = {
  job_id: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  download_url?: string;
};

export default function CostsPage() {
  const { token, user } = useAuth();
  const [companyId, setCompanyId] = useState<string>("");
  const [costs, setCosts] = useState<CostUpdate[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [activeTab, setActiveTab] = useState<string>("pending");
  const [exportJob, setExportJob] = useState<ExportJob | null>(null);
  const [exportLoading, setExportLoading] = useState(false);

  // fetch company id on mount
  useEffect(() => {
    const fetchCompany = async () => {
      const res = await apiFetch("/api/v1/auth/me", { token });
      if (res?.company_id) setCompanyId(res.company_id);
    };
    fetchCompany();
  }, [token]);

  // fetch costs whenever filter or company changes
  useEffect(() => {
    if (!companyId) return;
    const fetchCosts = async () => {
      const data = await apiFetch(
        `/api/v1/costs?company_id=${companyId}&status=${statusFilter}`,
        { token }
      );
      setCosts(data ?? []);
    };
    fetchCosts();
  }, [companyId, statusFilter, token]);

  const handleAction = async (id: string, action: "approve" | "reject") => {
    const reason = action === "reject" ? prompt("Rejection reason:") : undefined;
    await apiFetch(`/api/v1/costs/${id}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ action, reason }),
    });
    // refresh list
    setStatusFilter(statusFilter); // trigger reload
  };

  const startExport = async () => {
    setExportLoading(true);
    const job = await apiFetch(`/api/v1/export`, {
      method: "POST",
      token,
      body: JSON.stringify({ export_type: "costs", file_format: "csv" }),
    });
    setExportJob(job);
    setExportLoading(false);
  };

  // poll export job status
  useEffect(() => {
    if (!exportJob) return;
    const interval = setInterval(async () => {
      const status = await apiFetch(
        `/api/v1/export/jobs/${exportJob.job_id}`,
        { token }
      );
      setExportJob((prev) => (prev ? { ...prev, ...status } : prev));
      if (status.status === "completed" || status.status === "failed") {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [exportJob, token]);

  const isApprover = user?.roles?.some((r: string) => r.includes("cost_approver"));

  const columns = [
    { header: "Product", accessor: "product_name" },
    { header: "Supplier", accessor: "supplier_name" },
    { header: "Old Cost", accessor: "old_cost" },
    { header: "New Cost", accessor: "new_cost" },
    { header: "Source", accessor: "source" },
    { header: "Created At", accessor: "created_at" },
    { header: "Actions", accessor: "actions" },
  ];

  const renderRows = () =>
    costs.map((c) => (
      <tr key={c.id} className="border-b">
        <td className="px-4 py-2">{c.product_name}</td>
        <td className="px-4 py-2">{c.supplier_name}</td>
        <td className="px-4 py-2">{c.old_cost}</td>
        <td className="px-4 py-2">{c.new_cost}</td>
        <td className="px-4 py-2">{c.source}</td>
        <td className="px-4 py-2">{new Date(c.created_at).toLocaleString()}</td>
        <td className="px-4 py-2 space-x-2">
          {isApprover && c.status === "pending" && (
            <>
              <Button size="xs" color="green" onClick={() => handleAction(c.id, "approve")}>Approve</Button>
              <Button size="xs" color="red" onClick={() => handleAction(c.id, "reject")}>Reject</Button>
            </>
          )}
        </td>
      </tr>
    ));

  return (
    <DashboardLayout>
      <div className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">Cost Management</h1>
          <Button onClick={startExport} disabled={exportLoading}>
            {exportLoading ? <Loader size="xs" /> : "Export Costs"}
          </Button>
        </div>
        {exportJob && (
          <div className="mb-4">
            <Badge color={exportJob.status === "completed" ? "green" : exportJob.status === "failed" ? "red" : "blue"}>
              Export {exportJob.status}
            </Badge>
            {exportJob.status === "completed" && exportJob.download_url && (
              <a href={exportJob.download_url} className="ml-2 text-blue-600 underline">Download</a>
            )}
          </div>
        )}
        <div className="flex space-x-4 mb-4">
          <Select
            data={[{ value: "pending", label: "Pending" }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }]}
            value={statusFilter}
            onChange={(val) => val && setStatusFilter(val)}
            placeholder="Filter by status"
          />
        </div>
        <Tabs value={activeTab} onTabChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="pending">Pending Updates</Tabs.Tab>
            <Tabs.Tab value="history">History</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="pending" pt="xs">
            <Table striped highlightOnHover>
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col.header} className="px-4 py-2 text-left">{col.header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>{renderRows()}</tbody>
            </Table>
          </Tabs.Panel>
          <Tabs.Panel value="history" pt="xs">
            {/* History tab reuses same table but filtered by approved/rejected */}
            <Table striped highlightOnHover>
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col.header} className="px-4 py-2 text-left">{col.header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {costs
                  .filter((c) => c.status !== "pending")
                  .map((c) => (
                    <tr key={c.id} className="border-b">
                      <td className="px-4 py-2">{c.product_name}</td>
                      <td className="px-4 py-2">{c.supplier_name}</td>
                      <td className="px-4 py-2">{c.old_cost}</td>
                      <td className="px-4 py-2">{c.new_cost}</td>
                      <td className="px-4 py-2">{c.source}</td>
                      <td className="px-4 py-2">{new Date(c.created_at).toLocaleString()}</td>
                      <td className="px-4 py-2">{c.status.toUpperCase()}</td>
                    </tr>
                  ))}
              </tbody>
            </Table>
          </Tabs.Panel>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
