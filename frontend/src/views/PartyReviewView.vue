<script setup lang="ts">
import ExtensionLedger from "../components/ExtensionLedger.vue";
import type { LedgerColumn, LedgerField } from "../components/ledger-types";

const reviewColumns: LedgerColumn[] = [
  { key: "year", label: "年度", width: 80 },
  { key: "member_name", label: "党员", width: 100 },
  { key: "branch", label: "所属支部", width: 180 },
  { key: "self_rating", label: "自评", width: 90 },
  { key: "peer_rating", label: "互评", width: 90 },
  { key: "final_rating", label: "组织定格", width: 100 },
  { key: "status", label: "状态", width: 90 },
];

const reviewFields: LedgerField[] = [
  { key: "member_name", label: "党员姓名" },
  { key: "year", label: "年度", type: "number" },
  { key: "branch", label: "所属支部" },
  { key: "self_rating", label: "自评等次", type: "select", options: ["优秀", "合格", "基本合格", "不合格"] },
  { key: "peer_rating", label: "互评等次", type: "select", options: ["优秀", "合格", "基本合格", "不合格"] },
  { key: "final_rating", label: "组织定格", type: "select", options: ["优秀", "合格", "基本合格", "不合格", "未定格"] },
  { key: "status", label: "状态", type: "select", options: ["进行中", "已完成"] },
  { key: "issues_found", label: "查摆问题", type: "textarea" },
  { key: "rectification", label: "整改措施", type: "textarea" },
];

const indicatorColumns: LedgerColumn[] = [
  { key: "year", label: "年度", width: 80 },
  { key: "category", label: "指标分类", width: 140 },
  { key: "title", label: "考核指标", width: 320 },
  { key: "score", label: "分值", width: 80 },
  { key: "owner_role", label: "责任部门", width: 150 },
];

const indicatorFields: LedgerField[] = [
  { key: "title", label: "考核指标", span: 2 },
  { key: "year", label: "年度", type: "number" },
  { key: "category", label: "指标分类", type: "select", options: ["政治建设", "组织建设", "作风建设", "纪律建设", "作用发挥"] },
  { key: "score", label: "分值", type: "number" },
  { key: "owner_role", label: "责任部门" },
  { key: "description", label: "评分标准", type: "textarea" },
];

const checkColumns: LedgerColumn[] = [
  { key: "branch", label: "支部", width: 180 },
  { key: "category", label: "对标类别", width: 140 },
  { key: "item", label: "对标条目", width: 300 },
  { key: "compliant", label: "达标情况", width: 100 },
  { key: "checked_at", label: "自查日期", width: 110 },
];

const checkFields: LedgerField[] = [
  { key: "item", label: "对标条目", span: 2 },
  { key: "branch", label: "支部" },
  { key: "category", label: "对标类别", type: "select", options: ["组织设置", "班子建设", "组织生活", "功能作用", "基本保障"] },
  { key: "compliant", label: "达标情况", type: "select", options: ["达标", "基本达标", "不达标", "未查"] },
  { key: "checked_at", label: "自查日期", type: "date" },
  { key: "requirement", label: "标准要求", type: "textarea" },
  { key: "evidence", label: "佐证说明", type: "textarea" },
];
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="title-copy">
        <h1 class="page-title">考核评议</h1>
        <p class="page-description">民主评议党员、责任制考核指标与支部标准化对标自查。</p>
      </div>
    </header>
    <a-tabs default-active-key="review" type="rounded">
      <a-tab-pane key="review" title="民主评议党员">
        <ExtensionLedger
          resource="reviews"
          title="民主评议"
          :columns="reviewColumns"
          :fields="reviewFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
      <a-tab-pane key="indicators" title="责任制考核">
        <ExtensionLedger
          resource="indicators"
          title="考核指标"
          :columns="indicatorColumns"
          :fields="indicatorFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
      <a-tab-pane key="checks" title="支部标准化对标">
        <ExtensionLedger
          resource="checks"
          title="标准化对标自查"
          :columns="checkColumns"
          :fields="checkFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
