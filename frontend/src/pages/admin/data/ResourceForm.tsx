import { Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { useToast } from '@/components/ui/Toast';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useAll, useApiMutation } from '@/lib/query';

import { optionLabel } from './options';
import type { Field, Resource, Row } from './resources';

type Values = Record<string, unknown>;
type Errors = Record<string, string>;

const LANG_KEYS = ['uz', 'ru', 'en'] as const;

function initialValues(resource: Resource, row: Row | null): Values {
  const values: Values = {};
  for (const f of resource.fields) {
    if (f.type === 'translated') {
      for (const lang of LANG_KEYS) values[`${f.key}_${lang}`] = row?.[`${f.key}_${lang}`] ?? '';
    } else if (row) {
      values[f.key] = row[f.key] ?? (f.type === 'remotes' || f.type === 'choices' ? [] : '');
    } else if (f.type === 'boolean') {
      values[f.key] = ['is_active', 'is_hard'].includes(f.key);
    } else if (f.type === 'remotes' || f.type === 'choices') {
      values[f.key] = [];
    } else {
      values[f.key] = '';
    }
  }
  return values;
}

function payload(resource: Resource, values: Values): Values {
  const body: Values = {};
  for (const f of resource.fields) {
    if (f.type === 'translated') {
      for (const lang of LANG_KEYS) body[`${f.key}_${lang}`] = values[`${f.key}_${lang}`];
      continue;
    }
    const v = values[f.key];
    if (f.type === 'number') body[f.key] = v === '' ? null : Number(v);
    else if (f.type === 'remote' || (f.type === 'choice' && typeof f.values?.[1] === 'number'))
      body[f.key] = v === '' || v === null ? null : Number(v);
    else body[f.key] = v;
  }
  return body;
}

function parseErrors(err: unknown, fallback: string): { fields: Errors; general: string | null } {
  if (!(err instanceof ApiError)) return { fields: {}, general: fallback };
  const data = err.data as Record<string, unknown> | null;
  if (!data || typeof data !== 'object') return { fields: {}, general: err.detail ?? fallback };
  const fields: Errors = {};
  let general: string | null = err.detail ?? null;
  for (const [key, value] of Object.entries(data)) {
    const text = Array.isArray(value) ? value.join(' ') : String(value);
    if (key === 'non_field_errors' || key === 'detail') general = text;
    else fields[key] = text;
  }
  return { fields, general: general ?? (Object.keys(fields).length ? null : fallback) };
}

interface Props {
  resource: Resource;
  row: Row | null;
  readOnly: boolean;
  onClose: () => void;
}

export function ResourceForm({ resource, row, readOnly, onClose }: Props) {
  const { t } = useTranslation(['data', 'common']);
  const toast = useToast();
  const [values, setValues] = useState<Values>(() => initialValues(resource, row));
  const [errors, setErrors] = useState<Errors>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const save = useApiMutation<Values>(
    row ? 'PATCH' : 'POST',
    row ? `${resource.path}${row.id}/` : resource.path,
  );
  const remove = useApiMutation<void>('DELETE', `${resource.path}${row?.id}/`);
  const set = (key: string, value: unknown) => setValues((prev) => ({ ...prev, [key]: value }));
  const title = row
    ? t(`data:resources.${resource.key}.edit`)
    : t(`data:resources.${resource.key}.create`);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setGeneral(null);
    try {
      await save.mutateAsync(payload(resource, values));
      toast(t('data:saved'));
      onClose();
    } catch (err) {
      const parsed = parseErrors(err, t('common:errors.unknown'));
      setErrors(parsed.fields);
      setGeneral(parsed.general);
    }
  }

  async function onDelete() {
    try {
      await remove.mutateAsync();
      toast(t('data:deleted'));
      onClose();
    } catch (err) {
      setConfirmDelete(false);
      setGeneral(
        err instanceof ApiError && err.status === 403
          ? t('data:errors.forbidden')
          : err instanceof ApiError && err.status >= 400
            ? t('data:errors.inUse')
            : t('common:errors.unknown'),
      );
    }
  }

  const footer = readOnly ? (
    <Button variant="secondary" onClick={onClose}>
      {t('common:actions.close')}
    </Button>
  ) : (
    <>
      {row && (
        <Button
          variant="ghost"
          className="mr-auto text-danger-fg"
          icon={<Trash2 size={18} aria-hidden="true" />}
          onClick={() => setConfirmDelete(true)}
        >
          {t('data:actions.delete')}
        </Button>
      )}
      <Button variant="secondary" onClick={onClose}>
        {t('data:actions.cancel')}
      </Button>
      <Button type="submit" form="resource-form" disabled={save.isPending}>
        {save.isPending ? t('data:actions.saving') : t('data:actions.save')}
      </Button>
    </>
  );

  return (
    <>
      <Modal open title={title} onClose={onClose} variant="drawer" footer={footer}>
        <form id="resource-form" noValidate onSubmit={onSubmit} className="space-y-4">
          {general && (
            <p
              role="alert"
              className="rounded-button bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
            >
              {general}
            </p>
          )}
          <fieldset disabled={readOnly} className="space-y-4">
            {resource.fields.map((field) => (
              <FieldInput
                key={field.key}
                field={field}
                values={values}
                errors={errors}
                onChange={set}
              />
            ))}
          </fieldset>
        </form>
      </Modal>
      <Modal
        open={confirmDelete}
        size="sm"
        title={t('data:confirmDelete.title')}
        onClose={() => setConfirmDelete(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              {t('data:actions.cancel')}
            </Button>
            <Button
              className="bg-danger-fg hover:bg-danger-fg/90"
              onClick={onDelete}
              disabled={remove.isPending}
            >
              {t('data:actions.delete')}
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink">{t('data:confirmDelete.text')}</p>
      </Modal>
    </>
  );
}

function FieldInput({
  field,
  values,
  errors,
  onChange,
}: {
  field: Field;
  values: Values;
  errors: Errors;
  onChange: (key: string, value: unknown) => void;
}) {
  const { t } = useTranslation(['data']);
  const label = t(`data:fields.${field.label}`) + (field.required ? ' *' : '');
  const error = errors[field.key];

  if (field.type === 'translated') {
    return (
      <fieldset className="space-y-3 rounded-card border border-line p-4">
        <legend className="px-1 text-sm font-semibold text-ink">{label}</legend>
        {LANG_KEYS.map((lang) => {
          const key = `${field.key}_${lang}`;
          return (
            <Wrapped key={key} error={errors[key]}>
              <TextField
                label={t(`data:langs.${lang}`) + (lang === 'uz' ? ' *' : '')}
                value={String(values[key] ?? '')}
                onChange={(e) => onChange(key, e.target.value)}
                aria-invalid={Boolean(errors[key])}
              />
            </Wrapped>
          );
        })}
      </fieldset>
    );
  }
  if (field.type === 'boolean') {
    return (
      <label className="flex min-h-touch items-center gap-3 text-sm font-semibold text-ink">
        <input
          type="checkbox"
          className="h-5 w-5 accent-[rgb(var(--primary-700))]"
          checked={Boolean(values[field.key])}
          onChange={(e) => onChange(field.key, e.target.checked)}
        />
        {t(`data:fields.${field.label}`)}
      </label>
    );
  }
  if (field.type === 'choice') {
    return (
      <Wrapped error={error}>
        <Select
          label={label}
          value={String(values[field.key] ?? '')}
          onChange={(e) => onChange(field.key, e.target.value)}
          options={(field.values ?? []).map((v) => ({
            value: v,
            label: v === '' ? t('data:notSet') : t(`data:choices.${field.choices}.${v}`),
          }))}
        />
      </Wrapped>
    );
  }
  if (field.type === 'choices') {
    const selected = (values[field.key] as (string | number)[]) ?? [];
    return (
      <Wrapped error={error}>
        <ChipGroup
          label={label}
          options={(field.values ?? []).map((v) => ({
            value: v,
            label: t(`data:choices.${field.choices}.${v}`),
          }))}
          selected={selected}
          onChange={(next) => onChange(field.key, next)}
        />
      </Wrapped>
    );
  }
  if (field.type === 'remote' || field.type === 'remotes') {
    return (
      <RemoteInput field={field} label={label} values={values} error={error} onChange={onChange} />
    );
  }
  return (
    <Wrapped error={error}>
      <TextField
        label={label}
        type={{ number: 'number', time: 'time', date: 'date', text: 'text' }[field.type] ?? 'text'}
        min={field.min}
        max={field.max}
        value={String(values[field.key] ?? '').slice(0, field.type === 'time' ? 5 : undefined)}
        onChange={(e) => onChange(field.key, e.target.value)}
        aria-invalid={Boolean(error)}
      />
    </Wrapped>
  );
}

function RemoteInput({
  field,
  label,
  values,
  error,
  onChange,
}: {
  field: Field;
  label: string;
  values: Values;
  error?: string;
  onChange: (key: string, value: unknown) => void;
}) {
  const { t } = useTranslation(['data']);
  const { rows, isLoading } = useAll<{ id: number } & Record<string, unknown>>(field.path ?? null);
  const options = rows.map((r) => ({ value: r.id, label: optionLabel(r) }));
  if (field.type === 'remotes') {
    return (
      <Wrapped error={error}>
        <ChipGroup
          label={label}
          options={options}
          selected={(values[field.key] as number[]) ?? []}
          onChange={(next) => onChange(field.key, next)}
          searchable
        />
      </Wrapped>
    );
  }
  return (
    <Wrapped error={error}>
      <Select
        label={label}
        value={String(values[field.key] ?? '')}
        onChange={(e) => onChange(field.key, e.target.value)}
        placeholder={isLoading ? t('data:loadingOptions') : t('data:choose')}
        options={options}
      />
    </Wrapped>
  );
}

function ChipGroup({
  label,
  options,
  selected,
  onChange,
  searchable,
}: {
  label: string;
  options: { value: string | number; label: string }[];
  selected: (string | number)[];
  onChange: (next: (string | number)[]) => void;
  searchable?: boolean;
}) {
  const { t } = useTranslation(['data']);
  const [filter, setFilter] = useState('');
  const visible = options.filter((o) => o.label.toLowerCase().includes(filter.toLowerCase()));
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-ink">{label}</legend>
      {searchable && options.length > 12 && (
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('data:actions.search')}
          aria-label={t('data:actions.search')}
          className="mb-2 min-h-touch w-full rounded-button border border-line bg-card px-4 text-base"
        />
      )}
      <div className="flex max-h-56 flex-wrap gap-2 overflow-y-auto">
        {visible.map((o) => {
          const on = selected.some((s) => String(s) === String(o.value));
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={on}
              onClick={() =>
                onChange(
                  on
                    ? selected.filter((s) => String(s) !== String(o.value))
                    : [...selected, o.value],
                )
              }
              className={cn(
                'min-h-[36px] rounded-full border px-3 text-sm font-semibold transition-colors',
                on
                  ? 'border-primary-700 bg-primary-700 text-ink-on-primary'
                  : 'border-line bg-card text-ink',
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

function Wrapped({ error, children }: { error?: string; children: ReactNode }) {
  return (
    <div>
      {children}
      {error && (
        <p role="alert" className="mt-1 text-sm font-medium text-danger-fg">
          {error}
        </p>
      )}
    </div>
  );
}
