"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useUi } from "../common/AppProviders";
import api from "@/lib/axios";
import CreateHistoryPopup, { type HistoryPopupForm } from "./popup/CreateHistoryPopup";
import EditHistoryPopup, { type HistoryPopupRow } from "./popup/EditHistoryPopup";

type HistoryRow = HistoryPopupRow;

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
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<HistoryRow | null>(null);

  const boardList = async () => {
    try {
      await ui.withLoading(async () => {
        const response = await api.post("/ocrSelect", {});
        const boardList = response.data?.resultMap?.boardList || [];
        setRows(boardList);
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

      return matchKeyword && matchTemplate && matchFrom && matchTo;
    });
  }, [rows, query, template, dateFrom, dateTo]);

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

  return (
    <>
      <div className="hw-root">
        <div className="ms-card hw-filter-bar">
          <div className="hw-filter-row">
            <div className="hw-filter-group">
              <div className="hw-filter-label">Date</div>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="ms-input hw-input-date"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="ms-input hw-input-date"
              />
            </div>

            <div className="hw-filter-group">
              <div className="hw-filter-label">Template</div>
              <select
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                className="ms-select hw-select"
              >
                <option value="">All</option>
                {templateOptions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>

            <div className="hw-filter-search">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="템플릿명 검색"
                className="ms-input hw-search-input"
              />
              <button type="button" className="ms-btn" onClick={() => void boardList()}>
                검색
              </button>
            </div>

            <div className="hw-filter-group">
              <button type="button" className="ms-btn" onClick={() => void resetFilter()}>
                리셋
              </button>
              <button type="button" className="hw-btn-primary" onClick={() => setIsCreateOpen(true)}>
                생성
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
                  <th className="hw-th">OCR JOB ID</th>
                  <th className="hw-th">파일명</th>
                  <th className="hw-th">템플릿 명</th>
                  <th className="hw-th-action">재실행</th>
                  <th className="hw-th-action">내보내기</th>
                  <th className="hw-th-action">수정</th>
                  <th className="hw-th-action">삭제</th>
                  <th className="hw-th-time">실행시간</th>
                  <th className="hw-th-date">생성시간</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="hw-empty-td">
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
                  filteredRows.map((row) => (
                    <tr key={row.job_id} className="hw-tbody-row">
                      <td className="hw-td-bold">{row.job_id}</td>
                      <td className="hw-td">{row.file_name}</td>
                      <td className="hw-td">{row.template_name ?? "-"}</td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          onClick={() => { void runAction("rerun", row); }}
                        >
                          Run
                        </button>
                      </td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          onClick={() => { void runAction("export", row); }}
                        >
                          Export
                        </button>
                      </td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          onClick={() => {
                            setEditingRow(row);
                            setIsEditOpen(true);
                          }}
                        >
                          수정
                        </button>
                      </td>
                      <td className="hw-td-center">
                        <button
                          type="button"
                          className="ms-btn-sm"
                          onClick={() => void historyDelete(row.job_id)}
                        >
                          삭제
                        </button>
                      </td>
                      <td className="hw-td-center">
                        {formatProcessingTime(Number(row.processing_time))}
                      </td>
                      <td className="hw-td-muted">{row.created_at}</td>
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
