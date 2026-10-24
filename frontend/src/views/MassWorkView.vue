<script setup lang="ts">
import ExtensionLedger from "../components/ExtensionLedger.vue";
import type { LedgerColumn, LedgerField } from "../components/ledger-types";

const activityColumns: LedgerColumn[] = [
  { key: "title", label: "活动主题", width: 260 },
  { key: "held_at", label: "举办日期", width: 110 },
  { key: "location", label: "地点", width: 150 },
  { key: "participants", label: "参与人数", width: 100 },
  { key: "budget", label: "经费(元)", width: 110 },
  { key: "organizer", label: "承办", width: 140 },
  { key: "status", label: "状态", width: 90 },
];

const activityFields: LedgerField[] = [
  { key: "title", label: "活动主题", span: 2 },
  { key: "held_at", label: "举办日期", type: "date" },
  { key: "location", label: "地点" },
  { key: "participants", label: "参与人数", type: "number" },
  { key: "budget", label: "经费(元)", type: "number" },
  { key: "organizer", label: "承办单位" },
  { key: "status", label: "状态", type: "select", options: ["已举办", "筹备中", "已取消"] },
  { key: "summary", label: "活动概况", type: "textarea" },
];

const leagueMemberColumns: LedgerColumn[] = [
  { key: "name", label: "姓名", width: 100 },
  { key: "gender", label: "性别", width: 70 },
  { key: "branch", label: "所属团支部", width: 190 },
  { key: "league_post", label: "团内职务", width: 110 },
  { key: "league_joined_at", label: "入团时间", width: 110 },
  { key: "education", label: "学历", width: 100 },
  { key: "status", label: "状态", width: 90 },
];

const leagueMemberFields: LedgerField[] = [
  { key: "name", label: "姓名" },
  { key: "gender", label: "性别", type: "select", options: ["男", "女"] },
  { key: "branch", label: "所属团支部" },
  { key: "league_post", label: "团内职务", type: "select", options: ["团员", "团支部书记", "团支部副书记", "组织委员", "宣传委员"] },
  { key: "league_joined_at", label: "入团时间", type: "date" },
  { key: "education", label: "学历", type: "select", options: ["硕士研究生", "大学本科", "大学专科", "高中/中专"] },
  { key: "status", label: "状态", type: "select", options: ["在册", "离团", "组织关系转出"] },
  { key: "birth_date", label: "出生日期", type: "date" },
  { key: "notes", label: "备注", type: "textarea" },
];

const electionColumns: LedgerColumn[] = [
  { key: "branch", label: "团支部", width: 200 },
  { key: "term", label: "届次", width: 120 },
  { key: "election_date", label: "换届日期", width: 110 },
  { key: "new_secretary", label: "新任书记", width: 110 },
  { key: "committee", label: "委员会组成", width: 260 },
  { key: "approval_status", label: "报批状态", width: 100 },
];

const electionFields: LedgerField[] = [
  { key: "branch", label: "团支部" },
  { key: "term", label: "届次（如第十二届）" },
  { key: "election_date", label: "换届日期", type: "date" },
  { key: "new_secretary", label: "新任书记" },
  { key: "approval_status", label: "报批状态", type: "select", options: ["待报批", "已报批", "已批复"] },
  { key: "committee", label: "委员会组成", type: "textarea" },
  { key: "notes", label: "备注", type: "textarea" },
];
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="title-copy">
        <h1 class="page-title">群团工作</h1>
        <p class="page-description">工会与共青团活动、团员名册、团组织换届。</p>
      </div>
    </header>
    <a-tabs default-active-key="union" type="rounded">
      <a-tab-pane key="union" title="工会活动">
        <ExtensionLedger
          resource="activities"
          title="工会活动"
          :columns="activityColumns"
          :fields="activityFields"
          :fixed="{ kind: 'union' }"
          :query="{ kind: 'union' }"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
      <a-tab-pane key="league" title="团委活动">
        <ExtensionLedger
          resource="activities"
          title="团委活动"
          :columns="activityColumns"
          :fields="activityFields"
          :fixed="{ kind: 'league' }"
          :query="{ kind: 'league' }"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
      <a-tab-pane key="league-members" title="团员名册">
        <ExtensionLedger
          resource="league-members"
          title="团员名册"
          :columns="leagueMemberColumns"
          :fields="leagueMemberFields"
          show-summary
          :summary-keys="['total', '在册']"
        />
      </a-tab-pane>
      <a-tab-pane key="elections" title="团组织换届">
        <ExtensionLedger
          resource="elections"
          title="换届记录"
          :columns="electionColumns"
          :fields="electionFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
