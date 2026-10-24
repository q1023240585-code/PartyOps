<script setup lang="ts">
import ExtensionLedger from "../components/ExtensionLedger.vue";
import type { LedgerColumn, LedgerField } from "../components/ledger-types";

const brandColumns: LedgerColumn[] = [
  { key: "title", label: "品牌名称", width: 200 },
  { key: "category", label: "类别", width: 110 },
  { key: "slogan", label: "品牌口号", width: 240 },
  { key: "status", label: "状态", width: 100 },
  { key: "started_at", label: "创建时间", width: 110 },
  { key: "owner", label: "创建支部/部门", width: 160 },
];

const brandFields: LedgerField[] = [
  { key: "title", label: "品牌名称" },
  { key: "category", label: "类别", type: "select", options: ["党建品牌", "文化品牌", "劳模工匠品牌", "青年品牌"] },
  { key: "slogan", label: "品牌口号", span: 2 },
  { key: "started_at", label: "创建时间", type: "date" },
  { key: "status", label: "状态", type: "select", options: ["培育中", "已建成", "推广中"] },
  { key: "owner", label: "创建支部/部门" },
  { key: "description", label: "品牌内涵", type: "textarea" },
  { key: "highlights", label: "建设成效", type: "textarea" },
];

const opinionColumns: LedgerColumn[] = [
  { key: "title", label: "舆情事项", width: 260 },
  { key: "source", label: "来源平台", width: 120 },
  { key: "occurred_at", label: "发生时间", width: 110 },
  { key: "severity", label: "程度", width: 90 },
  { key: "status", label: "处置状态", width: 100 },
  { key: "responder", label: "责任人", width: 100 },
];

const opinionFields: LedgerField[] = [
  { key: "title", label: "舆情事项", span: 2 },
  { key: "source", label: "来源平台", type: "select", options: ["微信", "微博", "抖音", "网站留言", "内部反映", "其他"] },
  { key: "occurred_at", label: "发生时间", type: "date" },
  { key: "severity", label: "程度", type: "select", options: ["一般", "较大", "重大"] },
  { key: "status", label: "处置状态", type: "select", options: ["登记", "处置中", "已办结"] },
  { key: "responder", label: "责任人" },
  { key: "summary", label: "情况摘要", type: "textarea" },
  { key: "disposition", label: "处置措施", type: "textarea" },
];
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="title-copy">
        <h1 class="page-title">宣传文化</h1>
        <p class="page-description">文化品牌建设与舆情登记处置台账。</p>
      </div>
    </header>
    <a-tabs default-active-key="brands" type="rounded">
      <a-tab-pane key="brands" title="文化品牌">
        <ExtensionLedger
          resource="brands"
          title="文化品牌"
          :columns="brandColumns"
          :fields="brandFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
      <a-tab-pane key="opinions" title="舆情台账">
        <ExtensionLedger
          resource="opinions"
          title="舆情登记处置"
          :columns="opinionColumns"
          :fields="opinionFields"
          show-summary
          :summary-keys="['total']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
