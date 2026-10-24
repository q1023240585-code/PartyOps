<script setup lang="ts">
import ExtensionLedger from "../components/ExtensionLedger.vue";
import type { LedgerColumn, LedgerField } from "../components/ledger-types";

const incomeColumns: LedgerColumn[] = [
  { key: "member_name", label: "党员", width: 100 },
  { key: "branch", label: "所属支部", width: 180 },
  { key: "year", label: "年度", width: 80 },
  { key: "month", label: "月份", width: 70 },
  { key: "base_amount", label: "计算基数(月)", width: 120 },
  { key: "ratio", label: "比例", width: 90 },
  { key: "amount", label: "实缴金额", width: 100 },
  { key: "status", label: "状态", width: 90 },
  { key: "paid_at", label: "缴纳日期", width: 110 },
  { key: "method", label: "方式", width: 90 },
];

const incomeFields: LedgerField[] = [
  { key: "member_name", label: "党员姓名" },
  { key: "branch", label: "所属支部" },
  { key: "year", label: "年度", type: "number" },
  { key: "month", label: "月份", type: "number" },
  { key: "base_amount", label: "月计算基数(元)", type: "number" },
  { key: "ratio", label: "比例(如0.005)", type: "number" },
  { key: "amount", label: "实缴金额(元)", type: "number" },
  { key: "status", label: "状态", type: "select", options: ["已缴", "未缴", "减免"] },
  { key: "paid_at", label: "缴纳日期", type: "date" },
  { key: "method", label: "缴纳方式", type: "select", options: ["现金", "转账", "代扣"] },
  { key: "notes", label: "备注", type: "textarea" },
];

const expenseColumns: LedgerColumn[] = [
  { key: "purpose", label: "使用事项", width: 260 },
  { key: "year", label: "年度", width: 80 },
  { key: "amount", label: "金额(元)", width: 110 },
  { key: "approver", label: "审批人", width: 100 },
  { key: "paid_at", label: "支出日期", width: 110 },
  { key: "status", label: "状态", width: 90 },
];

const expenseFields: LedgerField[] = [
  { key: "purpose", label: "使用事项", span: 2 },
  { key: "year", label: "年度", type: "number" },
  { key: "amount", label: "金额(元)", type: "number" },
  { key: "approver", label: "审批人" },
  { key: "paid_at", label: "支出日期", type: "date" },
  { key: "status", label: "状态", type: "select", options: ["已支出", "待审批"] },
  { key: "notes", label: "备注", type: "textarea" },
];
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="title-copy">
        <h1 class="page-title">党费管理</h1>
        <p class="page-description">党费收缴与使用台账，按月登记、年度汇总。</p>
      </div>
    </header>
    <a-tabs default-active-key="income" type="rounded">
      <a-tab-pane key="income" title="收缴台账">
        <ExtensionLedger
          resource="fees"
          title="党费收缴"
          :columns="incomeColumns"
          :fields="incomeFields"
          :fixed="{ kind: 'income' }"
          :query="{ kind: 'income' }"
          show-summary
          :summary-keys="['income_total', 'unpaid', 'total']"
        />
      </a-tab-pane>
      <a-tab-pane key="expense" title="使用台账">
        <ExtensionLedger
          resource="fees"
          title="党费使用"
          :columns="expenseColumns"
          :fields="expenseFields"
          :fixed="{ kind: 'expense' }"
          :query="{ kind: 'expense' }"
          show-summary
          :summary-keys="['expense_total']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
