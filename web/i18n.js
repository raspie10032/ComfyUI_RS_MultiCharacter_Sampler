// SPDX-License-Identifier: GPL-3.0-only
import { zhMessages } from "./zh_messages.js";

export function chineseLocale(value = "en") {
    const locale = String(value).replaceAll("_", "-").toLowerCase();
    if (!/^zh(?:-|$)/.test(locale)) return null;
    return /(?:^|-)(?:hant|tw|hk|mo)(?:-|$)/.test(locale) ? "zh-TW" : "zh";
}

// Compile variable-bearing display messages once; values remain text only.
const variableMessages = Object.entries(zhMessages).filter(([key]) => /\{\d+\}/.test(key)).map(([key, translations]) => {
    const parts = key.split(/(\{\d+\})/);
    const ids = [];
    const pattern = parts.map(part => {
        if (/^\{\d+\}$/.test(part)) { ids.push(part.slice(1, -1)); return "([\\s\\S]*?)"; }
        return part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }).join("");
    return { regex: new RegExp("^" + pattern + "$"), ids, translations };
});

export function chineseText(english, locale) {
    const language = chineseLocale(locale);
    if (!language || typeof english !== "string") return english;
    const index = language === "zh-TW" ? 1 : 0;
    if (Object.hasOwn(zhMessages, english)) return zhMessages[english][index];
    for (const {regex, ids, translations} of variableMessages) {
        const match = regex.exec(english);
        if (!match) continue;
        const values = Object.fromEntries(ids.map((id, i) => [id, match[i + 1]]));
        return translations[index].replace(/\{(\d+)\}/g, (_, id) => values[id]);
    }
    return english;
}
