/**
 * @file distancia.hpp
 * @brief Distancia euclidea exacta hasta una region de la grilla.
 *
 * Es lo que usa el motor para correr un contorno hacia afuera (la cresta sale del
 * pie corrido el avance de la cara) y para preguntar si en una seccion cabe un
 * banco completo.
 *
 * La referencia en Python la calcula por fuerza bruta sobre una ventana del
 * radio pedido: exacta, pero cuesta O(celdas * offsets) y el numero de offsets
 * crece con el cuadrado del radio. Aca se usa la transformada de distancia de
 * Felzenszwalb & Huttenlocher (2012), que da EXACTAMENTE lo mismo en O(celdas),
 * sin importar el radio. Por eso el nucleo no necesita el tope de radio que la
 * version de Python si necesita para no volverse impagable.
 *
 * El recorte en radio_max se aplica al final, para conservar la misma semantica
 * que la referencia: mas alla del radio pedido, infinito.
 *
 * @copyright 2026 PitPy
 */
#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

namespace pitpy {
namespace detalle {

/// Centinela grande pero FINITO. Con infinito la parabola de corte da 0/0.
inline constexpr double kLejos = 1e20;

/**
 * @brief Transformada de distancia al cuadrado de una muestra unidimensional.
 *
 * Envolvente inferior de las parabolas centradas en cada muestra. `v` y `z` son
 * memoria de trabajo del tamano de la muestra (v) y uno mas (z), que el llamador
 * reserva una sola vez para no pedir memoria por fila.
 */
inline void dt1(const double* f, double* d, std::size_t n,
                std::int64_t* v, double* z) noexcept {
    std::int64_t k = 0;
    v[0] = 0;
    z[0] = -kLejos;
    z[1] = kLejos;
    for (std::size_t q = 1; q < n; ++q) {
        const double fq = f[q] + static_cast<double>(q) * static_cast<double>(q);
        double s;
        // Retrocede mientras la parabola nueva tape a la ultima. z[0] = -kLejos
        // garantiza que el retroceso termina en k == 0.
        while (true) {
            const double fv = f[v[k]] + static_cast<double>(v[k]) * static_cast<double>(v[k]);
            s = (fq - fv) / (2.0 * static_cast<double>(q) - 2.0 * static_cast<double>(v[k]));
            if (s > z[k]) {
                break;
            }
            --k;
        }
        ++k;
        v[k] = static_cast<std::int64_t>(q);
        z[k] = s;
        z[k + 1] = kLejos;
    }
    k = 0;
    for (std::size_t q = 0; q < n; ++q) {
        while (z[k + 1] < static_cast<double>(q)) {
            ++k;
        }
        const double dq = static_cast<double>(q) - static_cast<double>(v[k]);
        d[q] = dq * dq + f[v[k]];
    }
}

}   // namespace detalle

/**
 * @brief Distancia en metros de cada celda hasta la celda marcada mas cercana.
 *
 * Vale 0 dentro de la region marcada e infinito mas alla de radio_max.
 *
 * @param mascara ny*nx bytes, distinto de cero donde esta la region.
 * @param d       salida, ny*nx doubles.
 */
inline void distancia_hasta(const std::uint8_t* mascara, std::size_t ny, std::size_t nx,
                            double paso, double radio_max, double* d) noexcept {
    if (ny == 0 || nx == 0) {
        return;
    }
    const double inf = std::numeric_limits<double>::infinity();

    std::vector<double> f(ny > nx ? ny : nx);
    std::vector<double> tmp(ny > nx ? ny : nx);
    std::vector<std::int64_t> v(ny > nx ? ny : nx);
    std::vector<double> z((ny > nx ? ny : nx) + 1);

    // Paso 1: por filas.
    for (std::size_t i = 0; i < ny; ++i) {
        for (std::size_t j = 0; j < nx; ++j) {
            f[j] = mascara[i * nx + j] ? 0.0 : detalle::kLejos;
        }
        detalle::dt1(f.data(), tmp.data(), nx, v.data(), z.data());
        for (std::size_t j = 0; j < nx; ++j) {
            d[i * nx + j] = tmp[j];
        }
    }

    // Paso 2: por columnas, sobre el resultado del paso 1.
    for (std::size_t j = 0; j < nx; ++j) {
        for (std::size_t i = 0; i < ny; ++i) {
            f[i] = d[i * nx + j];
        }
        detalle::dt1(f.data(), tmp.data(), ny, v.data(), z.data());
        for (std::size_t i = 0; i < ny; ++i) {
            d[i * nx + j] = tmp[i];
        }
    }

    // De distancia al cuadrado en celdas a metros, con el recorte del radio.
    const double radio2 = (radio_max / paso) * (radio_max / paso);
    for (std::size_t k = 0; k < ny * nx; ++k) {
        d[k] = (d[k] > radio2) ? inf : std::sqrt(d[k]) * paso;
    }
}

}   // namespace pitpy
