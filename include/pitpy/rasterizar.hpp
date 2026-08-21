/**
 * @file rasterizar.hpp
 * @brief De la malla de triangulos a la grilla regular z(x, y).
 *
 * Es el kernel que mas duele en Python: su costo no escala con la cantidad de
 * caras sino con la cantidad de CELDAS que esas caras cubren, y en un pit de
 * 4 km a paso de 2 m eso son 4 millones de celdas (66 s en el interprete).
 *
 * La implementacion es deliberadamente la MISMA que la de referencia en
 * src/pitpy/superficie.py, formula por formula, incluyendo el orden de las
 * operaciones en coma flotante y las tolerancias. tests/test_nucleo.py exige que
 * las dos den identico resultado: si esta se "mejora" por su cuenta, ese test
 * cae. Es a proposito.
 *
 * @copyright 2026 PitPy
 */
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>

namespace pitpy {

/**
 * @brief Rasteriza triangulos a una grilla, quedandose con la cota mas baja.
 *
 * El centro de la celda (i, j) esta en x = x0 + (j + 0.5) * paso,
 * y = y0 + (i + 0.5) * paso. Las celdas sin superficie quedan en NaN.
 *
 * Se queda con el minimo porque la carcaza es un tazon: si dos caras se pisan en
 * planta, lo que interesa es el piso, no un techo.
 *
 * @param tris  n_tris * 9 doubles: (ax,ay,az, bx,by,bz, cx,cy,cz) por triangulo.
 * @param z     salida, ny * nx doubles, en orden de filas.
 */
inline void rasterizar(const double* tris, std::size_t n_tris,
                       double x0, double y0, double paso,
                       double* z, std::size_t ny, std::size_t nx) noexcept {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    for (std::size_t k = 0; k < ny * nx; ++k) {
        z[k] = nan;
    }
    if (paso <= 0.0 || ny == 0 || nx == 0) {
        return;
    }

    for (std::size_t t = 0; t < n_tris; ++t) {
        const double* v = tris + t * 9;
        const double ax = v[0], ay = v[1], az = v[2];
        const double bx = v[3], by = v[4], bz = v[5];
        const double cx = v[6], cy = v[7], cz = v[8];

        const double det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
        if (det == 0.0) {
            continue;   // triangulo degenerado en planta: no aporta cota
        }

        // Caja del triangulo en celdas, con un margen de una celda a cada lado
        // (el mismo que usa la referencia en Python).
        const double min_x = std::min(ax, std::min(bx, cx));
        const double max_x = std::max(ax, std::max(bx, cx));
        const double min_y = std::min(ay, std::min(by, cy));
        const double max_y = std::max(ay, std::max(by, cy));

        long long j0 = static_cast<long long>((min_x - x0) / paso) - 1;
        long long j1 = static_cast<long long>((max_x - x0) / paso) + 1;
        long long i0 = static_cast<long long>((min_y - y0) / paso) - 1;
        long long i1 = static_cast<long long>((max_y - y0) / paso) + 1;

        j0 = std::max<long long>(0, j0);
        i0 = std::max<long long>(0, i0);
        j1 = std::min<long long>(static_cast<long long>(nx) - 1, j1);
        i1 = std::min<long long>(static_cast<long long>(ny) - 1, i1);

        for (long long i = i0; i <= i1; ++i) {
            const double py = y0 + (static_cast<double>(i) + 0.5) * paso;
            double* fila = z + static_cast<std::size_t>(i) * nx;
            for (long long j = j0; j <= j1; ++j) {
                const double px = x0 + (static_cast<double>(j) + 0.5) * paso;
                const double w1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det;
                const double w2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det;
                const double w3 = 1.0 - w1 - w2;
                if (w1 < -1e-9 || w2 < -1e-9 || w3 < -1e-9) {
                    continue;
                }
                const double zc = w1 * az + w2 * bz + w3 * cz;
                double& celda = fila[static_cast<std::size_t>(j)];
                if (std::isnan(celda) || zc < celda) {
                    celda = zc;
                }
            }
        }
    }
}

}   // namespace pitpy
