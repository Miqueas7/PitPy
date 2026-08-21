/**
 * @file contornos.hpp
 * @brief Marching squares: del campo escalar a anillos cerrados ordenados.
 *
 * Es de donde salen la linea de cresta y la de pie de cada banco. Seguir el
 * borde de las celdas daria una escalera del tamano del paso; interpolando sobre
 * el valor del campo el error baja a una fraccion de celda, y por eso se puede
 * usar un paso grueso sin que la cresta se vea aserrada en el CAD.
 *
 * Mismo algoritmo que la referencia en src/pitpy/superficie.py, incluido el
 * criterio para las sillas de montar y el descarte de anillos de menos de cuatro
 * puntos, y tambien el redondeo de las coordenadas a seis decimales.
 *
 * Ese redondeo NO es cosmetico y hay que conservarlo: dos cuadrados vecinos
 * calculan el punto de su lado compartido a partir de las mismas dos esquinas
 * pero en orden opuesto (t contra 1-t), asi que el resultado difiere en el
 * ultimo bit. Sin redondear, el encadenado no reconoce que es el mismo punto y
 * el anillo sale partido en dos. Se probo: el contorno de un cono daba dos
 * anillos en vez de uno.
 *
 * @copyright 2026 PitPy
 */
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace pitpy {

using Punto = std::array<double, 3>;
using Anillo = std::vector<Punto>;

namespace detalle {

/// Clave exacta de un punto en planta: los bits de sus dos coordenadas.
struct Clave {
    std::uint64_t x;
    std::uint64_t y;
    bool operator==(const Clave& o) const noexcept { return x == o.x && y == o.y; }
};

struct HashClave {
    std::size_t operator()(const Clave& c) const noexcept {
        return static_cast<std::size_t>(c.x * 1000003ULL ^ c.y);
    }
};

inline Clave clave_de(const Punto& p) noexcept {
    Clave c{};
    std::memcpy(&c.x, &p[0], sizeof(double));
    std::memcpy(&c.y, &p[1], sizeof(double));
    return c;
}

struct HashArista {
    std::size_t operator()(const std::pair<Clave, Clave>& a) const noexcept {
        HashClave h;
        return h(a.first) * 31ULL ^ h(a.second);
    }
};

struct IgualArista {
    bool operator()(const std::pair<Clave, Clave>& a,
                    const std::pair<Clave, Clave>& b) const noexcept {
        return a.first == b.first && a.second == b.second;
    }
};

/// Arista sin direccion: se ordena para que (a,b) y (b,a) sean la misma.
inline std::pair<Clave, Clave> arista(const Clave& a, const Clave& b) noexcept {
    if (a.x < b.x || (a.x == b.x && a.y <= b.y)) {
        return {a, b};
    }
    return {b, a};
}

/// Redondeo a seis decimales, al par mas cercano: el mismo que hace round() de
/// Python. Ver la nota del encabezado: de esto depende que el anillo cierre.
inline double redondear6(double x) noexcept {
    return std::nearbyint(x * 1e6) / 1e6;
}

/// Donde cruza el valor entre dos esquinas, en fraccion de 0 a 1.
inline double corte(double v1, double v2, double valor) noexcept {
    if (!std::isfinite(v1) || !std::isfinite(v2)) {
        return 0.5;   // una esquina fuera de la superficie: al medio y seguimos
    }
    if (v2 == v1) {
        return 0.5;
    }
    const double t = (valor - v1) / (v2 - v1);
    return std::min(1.0, std::max(0.0, t));
}

inline double area_anillo(const Anillo& a) noexcept {
    double s = 0.0;
    for (std::size_t i = 0; i + 1 < a.size(); ++i) {
        s += a[i][0] * a[i + 1][1] - a[i + 1][0] * a[i][1];
    }
    return std::abs(s) / 2.0;
}

}   // namespace detalle

/**
 * @brief Anillos cerrados donde `campo` cruza `valor`. Dentro es campo <= valor.
 *
 * El campo se rodea de un borde "afuera" antes de recorrerlo: si la region llega
 * al borde del arreglo, el cruce no se ve y el anillo sale cortado.
 *
 * @return anillos del mas grande al mas chico, cada uno con el primer punto
 *         repetido al final.
 */
inline std::vector<Anillo> contornos(const double* campo, std::size_t ny_in, std::size_t nx_in,
                                     double valor, double paso,
                                     double x0_in, double y0_in, double z) {
    const std::size_t ny = ny_in + 2;
    const std::size_t nx = nx_in + 2;
    const double x0 = x0_in - paso;
    const double y0 = y0_in - paso;
    const double inf = std::numeric_limits<double>::infinity();

    std::vector<double> c(ny * nx, inf);
    for (std::size_t i = 0; i < ny_in; ++i) {
        for (std::size_t j = 0; j < nx_in; ++j) {
            c[(i + 1) * nx + (j + 1)] = campo[i * nx_in + j];
        }
    }
    std::vector<std::uint8_t> dentro(ny * nx);
    for (std::size_t k = 0; k < ny * nx; ++k) {
        dentro[k] = c[k] <= valor ? 1 : 0;
    }

    // Esquinas del cuadrado (i,j): k = 0,1,2,3 -> (i,j) (i,j+1) (i+1,j) (i+1,j+1)
    const int lados[4][2] = {{0, 1}, {1, 3}, {3, 2}, {2, 0}};

    auto punto = [&](std::size_t i, std::size_t j, int k1, int k2) noexcept {
        const std::size_t i1 = i + static_cast<std::size_t>(k1 / 2);
        const std::size_t j1 = j + static_cast<std::size_t>(k1 % 2);
        const std::size_t i2 = i + static_cast<std::size_t>(k2 / 2);
        const std::size_t j2 = j + static_cast<std::size_t>(k2 % 2);
        const double t = detalle::corte(c[i1 * nx + j1], c[i2 * nx + j2], valor);
        const double gi = static_cast<double>(i1) + t * (static_cast<double>(i2) - static_cast<double>(i1));
        const double gj = static_cast<double>(j1) + t * (static_cast<double>(j2) - static_cast<double>(j1));
        return Punto{detalle::redondear6(x0 + (gj + 0.5) * paso),
                     detalle::redondear6(y0 + (gi + 0.5) * paso), z};
    };

    std::vector<std::pair<Punto, Punto>> segmentos;
    for (std::size_t i = 0; i + 1 < ny; ++i) {
        for (std::size_t j = 0; j + 1 < nx; ++j) {
            const unsigned caso = static_cast<unsigned>(dentro[i * nx + j])
                                | static_cast<unsigned>(dentro[i * nx + j + 1]) << 1
                                | static_cast<unsigned>(dentro[(i + 1) * nx + j]) << 2
                                | static_cast<unsigned>(dentro[(i + 1) * nx + j + 1]) << 3;
            if (caso == 0 || caso == 15) {
                continue;
            }
            int cruza[4][2];
            int n_cruza = 0;
            for (const auto& l : lados) {
                const std::uint8_t a = dentro[(i + static_cast<std::size_t>(l[0] / 2)) * nx
                                              + j + static_cast<std::size_t>(l[0] % 2)];
                const std::uint8_t b = dentro[(i + static_cast<std::size_t>(l[1] / 2)) * nx
                                              + j + static_cast<std::size_t>(l[1] % 2)];
                if (a != b) {
                    cruza[n_cruza][0] = l[0];
                    cruza[n_cruza][1] = l[1];
                    ++n_cruza;
                }
            }
            auto agregar = [&](int a1, int a2, int b1, int b2) {
                const Punto p = punto(i, j, a1, a2);
                const Punto q = punto(i, j, b1, b2);
                if (p != q) {
                    segmentos.emplace_back(p, q);
                }
            };
            if (n_cruza == 2) {
                agregar(cruza[0][0], cruza[0][1], cruza[1][0], cruza[1][1]);
            } else if (n_cruza == 4) {
                // Silla de montar: se une por pares vecinos. Con que par se une es
                // ambiguo por definicion; a esta escala la diferencia es una celda.
                agregar(cruza[0][0], cruza[0][1], cruza[1][0], cruza[1][1]);
                agregar(cruza[2][0], cruza[2][1], cruza[3][0], cruza[3][1]);
            }
        }
    }

    // --- encadenado ---
    std::unordered_map<detalle::Clave, std::vector<Punto>, detalle::HashClave> vecinos;
    for (const auto& s : segmentos) {
        vecinos[detalle::clave_de(s.first)].push_back(s.second);
        vecinos[detalle::clave_de(s.second)].push_back(s.first);
    }

    std::unordered_set<std::pair<detalle::Clave, detalle::Clave>,
                       detalle::HashArista, detalle::IgualArista> vistos;
    std::vector<Anillo> anillos;
    for (const auto& s : segmentos) {
        const auto ar = detalle::arista(detalle::clave_de(s.first), detalle::clave_de(s.second));
        if (vistos.count(ar)) {
            continue;
        }
        Anillo anillo{s.first, s.second};
        vistos.insert(ar);
        while (true) {
            const Punto actual = anillo[anillo.size() - 1];
            const Punto previo = anillo[anillo.size() - 2];
            const auto it = vecinos.find(detalle::clave_de(actual));
            bool encontrado = false;
            Punto siguiente{};
            if (it != vecinos.end()) {
                for (const Punto& cand : it->second) {
                    if (cand == previo) {
                        continue;
                    }
                    const auto candidata = detalle::arista(detalle::clave_de(actual),
                                                           detalle::clave_de(cand));
                    if (vistos.count(candidata)) {
                        continue;
                    }
                    siguiente = cand;
                    encontrado = true;
                    break;
                }
            }
            if (!encontrado) {
                break;
            }
            vistos.insert(detalle::arista(detalle::clave_de(actual), detalle::clave_de(siguiente)));
            anillo.push_back(siguiente);
            if (siguiente == anillo[0]) {
                break;
            }
        }
        if (anillo.size() > 3) {
            if (!(anillo.front() == anillo.back())) {
                anillo.push_back(anillo.front());   // el anillo se corto en un borde
            }
            anillos.push_back(std::move(anillo));
        }
    }

    std::stable_sort(anillos.begin(), anillos.end(),
                     [](const Anillo& a, const Anillo& b) {
                         return detalle::area_anillo(a) > detalle::area_anillo(b);
                     });
    return anillos;
}

}   // namespace pitpy
