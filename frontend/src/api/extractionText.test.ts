import { describe, expect, it } from "vitest";
import { decodeTxtBytes, textIssue } from "./extractionText";

describe("entrada confirmada RF-30–RF-31", () => {
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
