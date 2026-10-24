<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Message, Modal } from "@arco-design/web-vue";
import { IconDelete, IconEdit, IconPlus, IconRefresh } from "@arco-design/web-vue/es/icon";
import { api } from "../api";

import type { LedgerColumn, LedgerField } from "./ledger-types";

const props = withDefaults(
  defineProps<{
    resource: string;
    title: string;
    columns: LedgerColumn[];
    fields: LedgerField[];
    fixed?: Record<string, unknown>;
    query?: Record<string, string | number>;
    showSummary?: boolean;
    summaryKeys?: string[];
  }>(),
  { fixed: () => ({}), query: () => ({}), showSummary: false, summaryKeys: () => [] },
);

type Row = Record<string, unknown> & { id: string; version: number };

const rows = ref<Row[]>([]);
const summary = ref<Record<string, unknown>>({});
const loading = ref(false);
const saving = ref(false);
const modalOpen = ref(false);
const editing = ref<Row | null>(null);
const form = ref<Record<string, unknown>>({});

const summaryItems = computed(() =>
  props.summaryKeys.map((key) => ({ key, value: summary.value[key] })),
);

function display(row: Row, key: string): string {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    return value.slice(0, 10);
  }
  return String(value);
}

async function load() {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(props.query)) {
      if (value !== "" && value !== 0) params.set(key, String(value));
    }
    const suffix = params.toString() ? `?${params.toString()}` : "";
    rows.value = await api.get<Row[]>(`/extension/${props.resource}${suffix}`);
    if (props.showSummary) {
      summary.value = await api.get<Record<string, unknown>>(`/extension/${props.resource}/summary`);
    }
  } catch (error) {
    Message.error(error instanceof Error ? error.message : "加载失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editing.value = null;
  form.value = {};
  for (const field of props.fields) {
    form.value[field.key] = field.type === "select" ? field.options?.[0] ?? "" : "";
  }
  modalOpen.value = true;
}

function openEdit(row: Row) {
  editing.value = row;
  form.value = {};
  for (const field of props.fields) {
    const value = row[field.key];
    form.value[field.key] =
      typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value) && field.type === "date"
        ? value.slice(0, 10)
        : value ?? "";
  }
  modalOpen.value = true;
}

async function save() {
  saving.value = true;
  try {
    const values = { ...props.fixed, ...form.value };
    if (editing.value) {
      await api.patch(`/extension/${props.resource}/${editing.value.id}`, { values });
      Message.success("已更新");
    } else {
      await api.post(`/extension/${props.resource}`, { values });
      Message.success("已登记");
    }
    modalOpen.value = false;
    await load();
  } catch (error) {
    Message.error(error instanceof Error ? error.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

function remove(row: Row) {
  Modal.confirm({
    title: "删除确认",
    content: `确定删除「${display(row, props.columns[1]?.key ?? "id")}」这条记录吗？`,
    okText: "删除",
    cancelText: "取消",
    onOk: async () => {
      try {
        await api.delete(`/extension/${props.resource}/${row.id}`);
        Message.success("已删除");
        await load();
      } catch (error) {
        Message.error(error instanceof Error ? error.message : "删除失败");
      }
    },
  });
}

onMounted(load);
defineExpose({ load });
</script>

<template>
  <section class="ledger">
    <header class="ledger-head">
      <div>
        <h3>{{ title }}</h3>
        <p v-if="showSummary && summaryItems.length" class="ledger-stats">
          <span v-for="item in summaryItems" :key="item.key">{{ item.key }}：{{ item.value ?? 0 }}</span>
        </p>
      </div>
      <a-space>
        <a-button size="small" @click="load"><template #icon><IconRefresh /></template>刷新</a-button>
        <a-button type="primary" size="small" @click="openCreate">
          <template #icon><IconPlus /></template>新增
        </a-button>
      </a-space>
    </header>
    <a-table
      :data="rows"
      :loading="loading"
      :pagination="{ pageSize: 12, showTotal: true }"
      row-key="id"
      :scroll="{ x: 900 }"
    >
      <a-table-column
        v-for="col in columns"
        :key="col.key"
        :title="col.label"
        :width="col.width"
      >
        <template #cell="{ record }">{{ display(record, col.key) }}</template>
      </a-table-column>
      <a-table-column title="操作" :width="130" fixed="right">
        <template #cell="{ record }">
          <a-button size="mini" @click="openEdit(record)"><template #icon><IconEdit /></template>编辑</a-button>
          <a-button size="mini" status="danger" @click="remove(record)">
            <template #icon><IconDelete /></template>删除
          </a-button>
        </template>
      </a-table-column>
    </a-table>

    <a-modal
      v-model:visible="modalOpen"
      :title="editing ? `编辑${title}` : `新增${title}`"
      :ok-loading="saving"
      @ok="save"
      @cancel="modalOpen = false"
    >
      <a-form :model="form" layout="vertical">
        <a-grid :cols="2" :col-gap="14">
          <a-grid-item
            v-for="field in fields"
            :key="field.key"
            :span="field.type === 'textarea' ? 2 : field.span ?? 1"
          >
            <a-form-item :label="field.label">
              <a-select v-if="field.type === 'select'" v-model="form[field.key]" :options="field.options?.map((o) => ({ label: o, value: o }))" />
              <a-date-picker v-else-if="field.type === 'date'" v-model="form[field.key]" style="width: 100%" />
              <a-input-number v-else-if="field.type === 'number'" v-model="form[field.key]" style="width: 100%" />
              <a-textarea v-else-if="field.type === 'textarea'" :model-value="String(form[field.key] ?? '')" :max-length="600" auto-size @update:model-value="(v: string) => (form[field.key] = v)" />
              <a-input v-else v-model="form[field.key]" :max-length="200" />
            </a-form-item>
          </a-grid-item>
        </a-grid>
      </a-form>
    </a-modal>
  </section>
</template>

<style scoped>
.ledger {
  display: grid;
  gap: 12px;
}

.ledger-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.ledger-head h3 {
  margin: 0;
  font-family: var(--serif);
  font-size: 18px;
  color: var(--charcoal);
}

.ledger-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 18px;
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.ledger-stats span::before {
  content: "";
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 6px;
  background: var(--cinnabar);
  border-radius: 1px;
  opacity: 0.7;
}
</style>
