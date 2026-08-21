/**
 * @file bindings.cpp
 * @brief Expone el nucleo C++ de PitPy a Python. Modulo: pitpy._nucleo
 *
 * Solo viven acá los kernels que en Python cuestan caro. Todo lo demas —el
 * modelo del dominio, las decisiones de geometria, los mensajes de error— se
 * queda en Python, donde se lee y se discute con el ingeniero.
 *
 * Los arreglos entran y salen como numpy sin copiar.
 *
 * @copyright 2026 PitPy
 */
#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

#include <cstddef>
#include <utility>

#include "pitpy/contornos.hpp"
#include "pitpy/distancia.hpp"
#include "pitpy/rasterizar.hpp"

namespace nb = nanobind;

using ArregloTriangulos =
    nb::ndarray<const double, nb::ndim<3>, nb::c_contig, nb::device::cpu>;
using ArregloMascara =
    nb::ndarray<const std::uint8_t, nb::ndim<2>, nb::c_contig, nb::device::cpu>;
using Grilla = nb::ndarray<nb::numpy, double, nb::ndim<2>>;

namespace {
/// Envuelve memoria propia como arreglo numpy, sin copiar.
Grilla entregar(double* datos, std::size_t ny, std::size_t nx) {
    nb::capsule dueno(datos, [](void* p) noexcept { delete[] static_cast<double*>(p); });
    return Grilla(datos, {ny, nx}, dueno);
}
}   // namespace

NB_MODULE(_nucleo, m) {
    m.doc() = "Nucleo C++ de PitPy: los kernels de grilla que en el interprete "
              "cuestan caro. La referencia legible de cada uno esta en "
              "src/pitpy/superficie.py y tests/test_nucleo.py exige que den lo mismo.";

    m.def(
        "rasterizar",
        [](ArregloTriangulos tris, double x0, double y0, double paso,
           std::size_t ny, std::size_t nx) {
            if (tris.shape(1) != 3 || tris.shape(2) != 3) {
                throw nb::value_error(
                    "se esperaba un arreglo de triangulos con forma (n, 3, 3)");
            }
            double* z = new double[ny * nx];
            {
                nb::gil_scoped_release sin_gil;   // el kernel no toca objetos Python
                pitpy::rasterizar(tris.data(), tris.shape(0), x0, y0, paso, z, ny, nx);
            }
            return entregar(z, ny, nx);
        },
        nb::arg("tris"), nb::arg("x0"), nb::arg("y0"), nb::arg("paso"),
        nb::arg("ny"), nb::arg("nx"),
        "Rasteriza triangulos (n,3,3) a una grilla (ny,nx), con NaN donde no hay "
        "superficie y la cota mas baja donde dos caras se pisan.");

    m.def(
        "distancia_hasta",
        [](ArregloMascara mascara, double paso, double radio_max) {
            const std::size_t ny = mascara.shape(0);
            const std::size_t nx = mascara.shape(1);
            double* d = new double[ny * nx];
            {
                nb::gil_scoped_release sin_gil;
                pitpy::distancia_hasta(mascara.data(), ny, nx, paso, radio_max, d);
            }
            return entregar(d, ny, nx);
        },
        nb::arg("mascara"), nb::arg("paso"), nb::arg("radio_max"),
        "Distancia en metros hasta la celda marcada mas cercana: 0 dentro de la "
        "region, infinito mas alla de radio_max. Exacta, en O(celdas).");

    m.def(
        "contornos",
        [](nb::ndarray<const double, nb::ndim<2>, nb::c_contig, nb::device::cpu> campo,
           double valor, double paso, double x0, double y0, double z) {
            std::vector<pitpy::Anillo> anillos;
            {
                nb::gil_scoped_release sin_gil;
                anillos = pitpy::contornos(campo.data(), campo.shape(0), campo.shape(1),
                                           valor, paso, x0, y0, z);
            }
            // Se arman tuplas de Python acá y no en el llamador: el motor entrega
            // list[Punto] por contrato (API_CONTRACTS), y convertir 96,000 puntos
            // en un lazo de Python costaba más que todo el resto del kernel.
            nb::list salida;
            for (const auto& anillo : anillos) {
                nb::list puntos;
                for (const auto& p : anillo) {
                    puntos.append(nb::make_tuple(p[0], p[1], p[2]));
                }
                salida.append(puntos);
            }
            return salida;
        },
        nb::arg("campo"), nb::arg("valor"), nb::arg("paso"), nb::arg("x0"),
        nb::arg("y0"), nb::arg("z"),
        "Anillos cerrados donde el campo cruza el valor, del mas grande al mas "
        "chico. Dentro es campo <= valor.");
}
