import { describe, expect, it } from "vitest";
import { decodeTxtBytes, textIssue, parseCorrection } from "./extractionText";

describe("entrada confirmada RF-30–RF-31", () => {
  it("corrige números ausentes y calendarios con sus tipos reales RF-09", () => {
    expect(parseCorrection("quantity", "2")).toBe(2);
    expect(parseCorrection("unit_area_m2", "35.5")).toBe(35.5);
    expect(parseCorrection("service_days", "lunes, miércoles")).toEqual([
      "lunes",
      "miércoles",
    ]);
    expect(() => parseCorrection("quantity", "2.5")).toThrow();
    expect(parseCorrection("quantity", "")).toBeNull();
  });
  it("cuenta emoji como un punto Unicode y bloquea el exceso", () => {
    expect(textIssue("😀".repeat(50000))).toBeNull();
    expect(textIssue("😀".repeat(50001))).toMatch(/50 000/);
    expect(textIssue(" \t\n")).toMatch(/solo espacios/);
  });
  it("acepta solo TXT UTF-8 estricto", () => {
    expect(
      decodeTxtBytes(
        "espacios.TXT",
        new TextEncoder().encode("Oficinas").buffer,
      ),
    ).toBe("Oficinas");
    expect(() => decodeTxtBytes("espacios.pdf", new ArrayBuffer(0))).toThrow(
      /Solo se admite TXT/,
    );
    expect(() =>
      decodeTxtBytes("espacios.txt", Uint8Array.of(0xff).buffer),
    ).toThrow(/UTF-8/);
  });
});
