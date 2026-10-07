import { describe, expect, it } from 'vitest';

type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

const files = import.meta.glob<Json>('./*/*.json', { eager: true, import: 'default' });
const LANGS = ['uz', 'ru', 'en'];

/** Flattens nested JSON to "a.b.c" keys; arrays keep their length as part of the key. */
function flatten(value: Json, prefix = ''): Map<string, Json> {
  const out = new Map<string, Json>();
  if (Array.isArray(value)) {
    out.set(`${prefix}[${value.length}]`, value);
    value.forEach((item, i) => flatten(item, `${prefix}[${i}]`).forEach((v, k) => out.set(k, v)));
  } else if (value !== null && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      flatten(v, prefix ? `${prefix}.${k}` : k).forEach((fv, fk) => out.set(fk, fv));
    }
  } else {
    out.set(prefix, value);
  }
  return out;
}

function catalog(lang: string): Map<string, Json> {
  const result = new Map<string, Json>();
  for (const [path, json] of Object.entries(files)) {
    const [, fileLang, file] = path.match(/^\.\/(\w+)\/(\w+)\.json$/)!;
    if (fileLang !== lang) continue;
    flatten(json).forEach((v, k) => result.set(`${file}:${k}`, v));
  }
  return result;
}

describe('translation catalogues', () => {
  const reference = catalog('uz');

  it('has a non-empty reference catalogue', () => {
    expect(reference.size).toBeGreaterThan(10);
  });

  it.each(LANGS.slice(1))('%s defines exactly the same keys as uz', (lang) => {
    const keys = [...catalog(lang).keys()].sort();
    expect(keys).toEqual([...reference.keys()].sort());
  });

  it.each(LANGS)('%s has no empty strings', (lang) => {
    const empty = [...catalog(lang)].filter(([, v]) => typeof v === 'string' && !v.trim());
    expect(empty).toEqual([]);
  });

  it.each(LANGS)('%s keeps the same interpolation variables', (lang) => {
    const vars = (s: Json) => [...String(s).matchAll(/{{\s*(\w+)\s*}}/g)].map((m) => m[1]).sort();
    const target = catalog(lang);
    for (const [key, value] of reference) {
      if (typeof value === 'string') expect(vars(target.get(key)!), key).toEqual(vars(value));
    }
  });
});
