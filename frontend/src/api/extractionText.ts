export function decodeTxtBytes(filename: string, bytes: ArrayBuffer): string {
  if (!filename.toLowerCase().endsWith(".txt"))
    throw new Error("Solo se admite TXT UTF-8.");
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw new Error("El TXT no puede leerse como UTF-8.");
  }
}

export function textIssue(text: string): string | null {
  if (/^[ \t\r\n]*$/.test(text))
    return "El texto no puede estar vacío o contener solo espacios.";
  if (Array.from(text).length > 50000)
    return "El texto supera 50 000 puntos de código Unicode.";
  return null;
}

export function parseCorrection(name: string, text: string): unknown {
  if (!text.trim()) return null;
  if (
    ["quantity", "visits_per_day", "unit_area_m2", "total_area_m2"].includes(
      name,
    )
  ) {
    const value = Number(text);
    if (
      !Number.isFinite(value) ||
      value <= 0 ||
      (["quantity", "visits_per_day"].includes(name) &&
        !Number.isInteger(value))
    )
      throw new Error(
        "Ingrese un número positivo; cantidad y visitas deben ser enteros.",
      );
    return value;
  }
  if (name === "service_days") {
    const values = text.trim().startsWith("[")
      ? JSON.parse(text)
      : text.split(",").map((day) => day.trim().toLowerCase());
    if (
      !Array.isArray(values) ||
      !values.every((day) => typeof day === "string")
    )
      throw new Error("Ingrese días separados por comas.");
    return values;
  }
  return text;
}
