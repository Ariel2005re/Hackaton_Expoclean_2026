// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Borradores from "./Borradores";
import { api } from "../api/client";
import { nuevoBorrador } from "../types/borrador";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("RF-28 lista borradores del servidor sin índice local", async () => {
  localStorage.clear();
  vi.spyOn(api, "listDrafts").mockResolvedValue([
    {
      ...nuevoBorrador(),
      id: "desde-otro-navegador",
      client: { name: "Cliente persistido", service_address: "Quito" },
    },
  ]);
  render(
    <MemoryRouter>
      <Borradores />
    </MemoryRouter>,
  );
  expect(
    (
      await screen.findByRole("link", { name: /Cliente persistido/ })
    ).getAttribute("href"),
  ).toBe("/borradores/desde-otro-navegador");
});
