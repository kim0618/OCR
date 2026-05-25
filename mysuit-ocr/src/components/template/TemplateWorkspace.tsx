"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useUi } from "../layout/AppProviders";

type TemplateRow = {
  template_id: string;
  template_name: string;
  field_count: number;
  created_at: string;
  updated_at: string;
};

type Props = {
  onNewTemplate: () => void;
};

export default function TemplateWorkspace({ onNewTemplate }: Props) {
  const ui = useUi();
  const [rows, setRows] = useState<TemplateRow[]>([]);
  const [query, setQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const loadList = async () => {
    try {
      await ui.withLoading(async () => {
        const res = await fetch("/templates");
        const json = await res.json();
        setRows(json.resultMap?.templateList ?? []);
      });
    } catch (error) {
      console.error(error);
      await ui.alert("템플릿 조회 중 오류가 발생했습니다.");
    }
  };

  const deleteTemplate = async (id: string, name: string) => {
    const ok = await ui.confirm({
      title: "삭제",
      message: `"${name}" 템플릿을 삭제할까요?`,
      okText: "확인",
      cancelText: "취소",
    });
    if (!ok) return;

    try {
      await ui.withLoading(async () => {
        await fetch(`/templates/${id}`, { method: "DELETE" });
        await loadList();
        await ui.alert("삭제되었습니다.");
      });
    } catch (error) {
      console.error(error);
      await ui.alert("삭제 중 오류가 발생했습니다.");
    }
  };

  useEffect(() => {
    void loadList();
  }, []);

  const filteredRows = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return rows.filter((row) => {
      const name = row.template_name ?? "";
      const createdDate = String(row.created_at ?? "").slice(0, 10);
      const matchKeyword = !keyword || name.toLowerCase().includes(keyword);
      const matchFrom = !dateFrom || createdDate >= dateFrom;
      const matchTo = !dateTo || createdDate <= dateTo;
      return matchKeyword && matchFrom && matchTo;
    });
  }, [rows, query, dateFrom, dateTo]);

  return (
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

          <div className="hw-filter-search">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="템플릿명 검색"
              className="ms-input hw-search-input"
            />
          </div>

          <div className="hw-filter-group">
            <button type="button" className="hw-btn-primary" onClick={onNewTemplate}>
              + New Template
            </button>
            <button type="button" className="ms-btn" onClick={() => {
              void ui.alert("템플릿 업로드 기능은 준비 중입니다.");
            }}>
              Upload
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
                <th className="hw-th">템플릿 ID</th>
                <th className="hw-th">템플릿 명</th>
                <th className="hw-th-action">필드 수</th>
                <th className="hw-th-action">편집</th>
                <th className="hw-th-action">삭제</th>
                <th className="hw-th-date">생성시간</th>
                <th className="hw-th-date">수정시간</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="hw-empty-td">
                    등록된 템플릿이 없습니다.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.template_id} className="hw-tbody-row">
                    <td className="hw-td-bold">{row.template_id}</td>
                    <td className="hw-td">{row.template_name}</td>
                    <td className="hw-td-center">{row.field_count}</td>
                    <td className="hw-td-center">
                      <button
                        type="button"
                        className="ms-btn-sm"
                        onClick={() => {
                          /* TODO: 편집 */
                          void ui.alert("편집 기능은 준비 중입니다.");
                        }}
                      >
                        편집
                      </button>
                    </td>
                    <td className="hw-td-center">
                      <button
                        type="button"
                        className="ms-btn-sm"
                        onClick={() => void deleteTemplate(row.template_id, row.template_name)}
                      >
                        삭제
                      </button>
                    </td>
                    <td className="hw-td-muted">{row.created_at}</td>
                    <td className="hw-td-muted">{row.updated_at}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
