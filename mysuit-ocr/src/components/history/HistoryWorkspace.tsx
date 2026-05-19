"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useUi } from "../common/AppProviders";
import api from "@/lib/axios";
import CreateHistoryPopup, { type HistoryPopupForm } from "./popup/CreateHistoryPopup";
import EditHistoryPopup, { type HistoryPopupRow } from "./popup/EditHistoryPopup";
import DetailHistoryView from "./DetailHistoryView";
import { readHistoryListWithFallback, readHistoryDetailWithFallback, deleteHistoryRun, type RunStatus, type HistoryRunRecord } from "@/lib/historyStore";

type HistoryRow = HistoryPopupRow & { status?: RunStatus };

function formatProcessingTime(value: number) {
  if (!Number.isFinite(value)) return "-";
  return `${value.toFixed(1)}s`;
}

function nowDateString() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export default function HistoryWorkspace() {
  const ui = useUi();
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [query, setQuery] = useState("");
  const [template, setTemplate] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState<"all" | "success" | "fail">("all");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<HistoryRow | null>(null);
  const [detailRecord, setDetailRecord] = useState<HistoryRunRecord | null>(null);
  const viewMode: "list" | "detail" = detailRecord ? "detail" : "list";

  // TEMP: 히스토리 DB 미구축 상태. RunOCR 에서 OCR 실행 시
  // localStorage 에 적재한 실행 기록을 읽어 표시한다.
  // DB 준비되면 `lib/historyStore` 만 교체하면 됨.
  // HISTORY-STRUCTURE-2B: mysuit_ocr_history_index 우선 조회, fallback → mysuit_ocr_history
  const boardList = async () => {
    try {
      await ui.withLoading(async () => {
        const list = readHistoryListWithFallback();
        const mapped: HistoryRow[] = list.map((r) => ({
          job_id: r.job_id,
          file_name: r.file_name,
          template_name: r.template_name,
          processing_time: r.processing_time,
          created_at: r.created_at,
          status: r.status,
        }));
        setRows(mapped);
      });
    } catch (error) {
      console.error(error);
      await ui.alert("히스토리 조회 중 오류가 발생했습니다.");
    }
  };


  const historyDelete = async (jobId: string) => {
    const ok = await ui.confirm({
      title: "삭제",
      message: `선택한 히스토리를 삭제할까요?\n(job_id: ${jobId})`,
      okText: "확인",
      cancelText: "취소",
    });

    if (!ok) return;

    try {
      await ui.withLoading(async () => {
        await api.post("/ocrDelete", {
          job_id: jobId,
        });

        await boardList();
        await ui.alert("삭제되었습니다.");
      });
    } catch (error) {
      console.error(error);
      await ui.alert("히스토리 삭제 중 오류가 발생했습니다.");
    }
  };

  const historyInsert = async (form: HistoryPopupForm) => {
    try {
      await ui.withLoading(async () => {
        await api.post("/ocrInsert", {
          file_name: form.file_name,
          template_name: form.template_name,
          processing_time: form.processing_time,
        });

        setIsCreateOpen(false);
        await boardList();
        await ui.alert("생성되었습니다.");
      });
    } catch (error) {
      console.error(error);
      await ui.alert("히스토리 생성 중 오류가 발생했습니다.");
    }
  };

  const historyUpdate = async (form: HistoryRow) => {
    try {
      await ui.withLoading(async () => {
        await api.post("/ocrUpdate", {
          job_id: form.job_id,
          file_name: form.file_name,
          template_name: form.template_name,
          processing_time: form.processing_time,
        });

        setIsEditOpen(false);
        setEditingRow(null);
        await boardList();
        await ui.alert("수정되었습니다.");
      });
    } catch (error) {
      console.error(error);
      await ui.alert("히스토리 수정 중 오류가 발생했습니다.");
    }
  };

  useEffect(() => {
    setDateTo(nowDateString());
    void boardList();
  }, []);

  const templateOptions = useMemo(() => {
    const set = new Set<string>();
    rows.forEach((row) => {
      if (row.template_name) set.add(row.template_name);
    });
    return Array.from(set).sort();
  }, [rows]);

  const filteredRows = useMemo(() => {
    const keyword = query.trim().toLowerCase();

    return rows.filter((row) => {
      const templateName = row.template_name ?? "";
      const createdDate = String(row.created_at ?? "").slice(0, 10);

      const matchKeyword = !keyword || templateName.toLowerCase().includes(keyword);

      const matchTemplate = !template || templateName === template;
      const matchFrom = !dateFrom || createdDate >= dateFrom;
      const matchTo = !dateTo || createdDate <= dateTo;
      const matchStatus = status === "all" || row.status === status;

      return matchKeyword && matchTemplate && matchFrom && matchTo && matchStatus;
    });
  }, [rows, query, template, dateFrom, dateTo, status]);

  const resetFilter = () => {
    setQuery("");
    setTemplate("");
    setDateFrom("");
    setDateTo(nowDateString());
  };

  const runAction = async (action: "rerun" | "export", row: HistoryRow) => {
    await ui.withLoading(async () => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await ui.alert(`${action.toUpperCase()} 실행: ${row.job_id}`);
    });
  };

  if (viewMode === "detail") {
    return (
      <div className="hw-root" style={{ height: "100%" }}>
        <DetailHistoryView
          item={detailRecord}
          onBack={() => setDetailRecord(null)}
          onSaved={(rec) => setDetailRecord(rec)}
        />
      </div>
    );
  }

  return (
    <>
      <div className="hw-root">
        <div className="ms-card hw-filter-bar">
          <div className="hw-filter-row">
            <div className="hw-filter-group">
              <div className="hw-filter-label">요청일시</div>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="ms-input hw-input-date"
              />
              <span className="hw-filter-separator">~</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="ms-input hw-input-date"
              />
            </div>

            <div className="hw-filter-group">
              <div className="hw-filter-label">상태</div>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as "all" | "success" | "fail")}
                className="ms-select hw-select"
              >
                <option value="all">전체</option>
                <option value="success">성공</option>
                <option value="fail">실패</option>
              </select>
            </div>

            <div className="hw-filter-group">
              <button type="button" className="hw-btn-primary" onClick={() => void boardList()}>
                조회
              </button>
            </div>
          </div>
        </div>

        <div className="hw-count">
          총 <b style={{ color: "var(--text)" }}>{filteredRows.length}</b>건
        </div>

        <div className="ms-card hw-table-wrap">
          <div className="hw-table-scroll">
            <table className="hw-table">
              <thead>
                <tr className="hw-thead-row">
                  <th className="hw-th">No</th>
                  <th className="hw-th">템플릿명</th>
                  <th className="hw-th">요청일시</th>
                  <th className="hw-th">상태</th>
                  <th className="hw-th">파일명</th>
                  <th className="hw-th-action">상세보기</th>
                  <th className="hw-th-action">삭제</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="hw-empty-td">
                      <svg width="36" height="36" viewBox="0 0 36 36" fill="none" style={{ margin: "0 auto 10px", display: "block", opacity: 0.35 }}>
                        <circle cx="18" cy="18" r="15" stroke="var(--muted)" strokeWidth="2"/>
                        <path d="M12 18h12M18 12v12" stroke="var(--muted)" strokeWidth="2" strokeLinecap="round" opacity="0.5"/>
                        <path d="M10 14h16M10 18h10M10 22h13" stroke="var(--muted)" strokeWidth="1.8" strokeLinecap="round"/>
                      </svg>
                      <div style={{ fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>기록이 없습니다</div>
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>OCR 작업을 실행하면 이곳에 이력이 쌓입니다</div>
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((row, index) => (
                    <tr key={row.job_id} className="hw-tbody-row">
                      <td className="hw-td-center">{index + 1}</td>
                      <td className="hw-td">{row.template_name ?? "-"}</td>
                      <td className="hw-td-muted">{row.created_at}</td>
                      <td className="hw-td-center">
                        {row.status === "success" ? "성공" : row.status === "fail" ? "실패" : "-"}
                      </td>
                      <td className="hw-td">{row.file_name}</td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          // HISTORY-STRUCTURE-2C: details 우선, fallback → mysuit_ocr_history
                          onClick={() => {
                            setDetailRecord(readHistoryDetailWithFallback(row.job_id));
                          }}
                        >
                          상세보기
                        </button>
                      </td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          onClick={async () => {
                            const ok = await ui.confirm({
                              title: "삭제",
                              message: `이 히스토리 행을 삭제할까요?\n${row.file_name} · ${row.created_at}`,
                              okText: "삭제",
                              cancelText: "취소",
                            });
                            if (!ok) return;
                            if (deleteHistoryRun(row.job_id)) {
                              await boardList();
                            } else {
                              await ui.alert("삭제 중 오류가 발생했습니다.");
                            }
                          }}
                        >
                          삭제
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <CreateHistoryPopup
        open={isCreateOpen}
        templateOptions={templateOptions}
        onClose={() => setIsCreateOpen(false)}
        onCreate={historyInsert}
      />

      <EditHistoryPopup
        open={isEditOpen}
        item={editingRow}
        templateOptions={templateOptions}
        onClose={() => {
          setIsEditOpen(false);
          setEditingRow(null);
        }}
        onUpdate={historyUpdate}
      />
    </>
  );
}
