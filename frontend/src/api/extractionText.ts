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
