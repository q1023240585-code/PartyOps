<script setup lang="ts">
import ExtensionLedger from "../components/ExtensionLedger.vue";
import type { LedgerColumn, LedgerField } from "../components/ledger-types";

const memberColumns: LedgerColumn[] = [
  { key: "name", label: "姓名", width: 100 },
  { key: "gender", label: "性别", width: 70 },
  { key: "branch", label: "所属支部", width: 180 },
  { key: "party_post", label: "党内职务", width: 110 },
  { key: "joined_party_at", label: "入党时间", width: 110 },
  { key: "member_kind", label: "类别", width: 100 },
  { key: "education", label: "学历", width: 100 },
  { key: "status", label: "状态", width: 90 },
  { key: "phone", label: "联系电话", width: 130 },
];

const memberFields: LedgerField[] = [
  { key: "name", label: "姓名" },
  { key: "gender", label: "性别", type: "select", options: ["男", "女"] },
  { key: "branch", label: "所属支部" },
  { key: "party_post", label: "党内职务", type: "select", options: ["党员", "支部书记", "支部副书记", "组织委员", "宣传委员", "纪检委员"] },
  { key: "joined_party_at", label: "入党时间", type: "date" },
  { key: "member_kind", label: "类别", type: "select", options: ["正式党员", "预备党员"] },
  { key: "education", label: "学历", type: "select", options: ["博士研究生", "硕士研究生", "大学本科", "大学专科", "中专及以下"] },
  { key: "status", label: "状态", type: "select", options: ["在册", "组织关系转出", "退休", "流动党员"] },
  { key: "phone", label: "联系电话" },
  { key: "birth_date", label: "出生日期", type: "date" },
  { key: "notes", label: "备注", type: "textarea" },
];

const trainingColumns: LedgerColumn[] = [
  { key: "title", label: "培训主题", width: 240 },
  { key: "category", label: "类别", width: 110 },
  { key: "start_date", label: "开始日期", width: 110 },
  { key: "end_date", label: "结束日期", width: 110 },
  { key: "hours", label: "学时", width: 80 },
  { key: "participants", label: "参训人数", width: 100 },
  { key: "branch", label: "组织支部", width: 170 },
];

const trainingFields: LedgerField[] = [
  { key: "title", label: "培训主题", span: 2 },
  { key: "category", label: "类别", type: "select", options: ["集中培训", "主题党日", "在线学习", "党课教育", "专题轮训"] },
  { key: "branch", label: "组织支部" },
  { key: "start_date", label: "开始日期", type: "date" },
  { key: "end_date", label: "结束日期", type: "date" },
  { key: "hours", label: "学时", type: "number" },
  { key: "participants", label: "参训人数", type: "number" },
  { key: "summary", label: "培训内容摘要", type: "textarea" },
];
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="title-copy">
        <h1 class="page-title">党员队伍</h1>
        <p class="page-description">党员名册与教育培训台账，一处维护、按需统计。</p>
      </div>
    </header>
    <a-tabs default-active-key="roster" type="rounded">
      <a-tab-pane key="roster" title="党员名册">
        <ExtensionLedger
          resource="members"
          title="党员名册"
          :columns="memberColumns"
          :fields="memberFields"
          show-summary
          :summary-keys="['total', '正式党员', '预备党员', '在册']"
        />
      </a-tab-pane>
      <a-tab-pane key="training" title="教育培训">
        <ExtensionLedger
          resource="trainings"
          title="教育培训台账"
          :columns="trainingColumns"
          :fields="trainingFields"
          show-summary
          :summary-keys="['total', 'hours_total', 'participants_total']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
