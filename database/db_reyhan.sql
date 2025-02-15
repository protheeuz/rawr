-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Feb 15, 2025 at 01:35 PM
-- Server version: 8.0.30
-- PHP Version: 7.4.32

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_reyhan`
--

-- --------------------------------------------------------

--
-- Table structure for table `admins`
--

CREATE TABLE `admins` (
  `id` int NOT NULL,
  `email` varchar(255) NOT NULL,
  `qualification` varchar(255) DEFAULT NULL,
  `job` varchar(255) DEFAULT NULL,
  `profile_picture` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `email_verification`
--

CREATE TABLE `email_verification` (
  `id` int NOT NULL,
  `email` varchar(255) NOT NULL,
  `verification_code` varchar(6) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `patients`
--

CREATE TABLE `patients` (
  `id` int NOT NULL,
  `nama` varchar(255) NOT NULL,
  `hasil_pemeriksaan` text,
  `confidence_score` float NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `patients`
--

INSERT INTO `patients` (`id`, `nama`, `hasil_pemeriksaan`, `confidence_score`, `created_at`) VALUES
(1, 'Bapak Mukhlis', 'Hasil deteksi: Kanker: Ya (Ganas) dengan kepercayaan 68.02468299865723%', 68.0247, '2025-02-10 12:22:28'),
(2, 'Mas Makhlus', 'Hasil deteksi: Kanker: Ya (Ganas) dengan kepercayaan 68.02468299865723%', 68.0247, '2025-02-10 12:29:09'),
(3, 'Suryanto', 'Hasil deteksi: Kanker: Tidak (Jinak)', 5.94175, '2025-02-10 12:32:38'),
(4, 'Bapak Yusup', 'Hasil deteksi: Kanker: Tidak (Jinak)', 5.41348, '2025-02-10 12:38:40'),
(5, 'Yanto Suryanto', 'Hasil deteksi: Kanker: Tidak (Jinak)', 3.60131, '2025-02-10 12:40:26'),
(6, 'Suryanto', 'Hasil deteksi: Kanker: Tidak (Jinak)', 0.00209916, '2025-02-10 12:41:31'),
(7, 'HARGA MAHAL TAPI LAKU', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 0, '2025-02-10 12:46:21'),
(8, 'Suryanto', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tidak.', 0, '2025-02-10 12:47:08'),
(9, 'HARGA MAHAL TAPI LAKU', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tidak.', 0, '2025-02-10 12:47:25'),
(10, 'Bapak Mukhlis', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tidak.', 0, '2025-02-10 12:47:41'),
(11, 'Yanto Suryanto', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tidak.', 0, '2025-02-10 12:48:18'),
(12, 'Yanto Suryanto', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tidak.', 0, '2025-02-10 12:49:36'),
(13, 'cc', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 3.6013, '2025-02-10 12:49:52'),
(14, 'cxcx', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 3.6013, '2025-02-10 12:50:21'),
(15, 'cvvv', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 3.6013, '2025-02-10 12:51:10'),
(16, 'asfasf', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 3.6013, '2025-02-10 12:52:06'),
(17, 'nihjk', 'Hasil Deteksi: Model tidak yakin mendeteksi gambar sebagai Kanker/Tumor.', 3.6013, '2025-02-10 12:53:01'),
(18, ' ijkjk ', 'Hasil Deteksi: Kanker: Tidak (Jinak)', 3.6013, '2025-02-10 12:53:50'),
(19, 'asfasf', 'Hasil Deteksi: Kanker: Tidak (Jinak)', 3.6013, '2025-02-10 12:54:28'),
(20, 'hnuiuijsd', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 12:59:24'),
(21, 'gsgsd', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 13:02:43'),
(22, 'dasdas', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 13:04:44'),
(23, 'dsadas', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 13:09:39'),
(24, 'gsdg', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 13:12:24'),
(25, 'gsdg', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-10 13:18:17'),
(26, 'Suryanto', 'Hasil deteksi: Tidak Kanker (Jinak)', 3.6013, '2025-02-11 14:00:45'),
(27, 'reyhan', 'Hasil deteksi: Tidak Kanker (Jinak)', 1.8365, '2025-02-15 12:50:19'),
(28, 'reyhan', 'Hasil deteksi: Kanker (Ganas)', 91.735, '2025-02-15 12:51:07'),
(29, 'reyhan', 'Hasil deteksi: Kanker (Ganas)', 99.9013, '2025-02-15 12:51:31'),
(30, 'reyhan', 'Hasil deteksi: Tidak Kanker (Jinak)', 1.8365, '2025-02-15 12:51:42'),
(31, 'reyhan', 'Hasil deteksi: Kanker (Ganas)', 95.6737, '2025-02-15 12:51:54'),
(32, 'reyhan', 'Hasil deteksi: Kanker (Ganas)', 99.9013, '2025-02-15 12:52:08'),
(33, 'vika', 'Hasil deteksi: Kanker (Ganas)', 95.6737, '2025-02-15 12:56:26'),
(34, 'mokar', 'Hasil deteksi: Kanker (Ganas)', 91.735, '2025-02-15 12:57:54'),
(35, 'reyhan', 'Hasil deteksi: Kanker (Ganas)', 95.6737, '2025-02-15 13:00:07'),
(36, 'mokar', 'Hasil deteksi: Kanker (Ganas)', 93.4133, '2025-02-15 13:00:37'),
(37, 'reyhan', 'Hasil deteksi: Tidak Kanker (Jinak)', 0.0027, '2025-02-15 13:01:12'),
(38, 'moko', 'Hasil deteksi: Tidak Kanker (Jinak)', 0.0016, '2025-02-15 13:01:48');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` enum('admin','pengunjung') NOT NULL,
  `profile_picture` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password`, `role`, `profile_picture`, `created_at`, `updated_at`) VALUES
(1, 'Mathtech Studio', 'mathtechstudio@gmail.com', '27c3cd09fc7370385cfed42f8aed4e7abf48048081dfda7770e4ae00e6748d6c', 'pengunjung', '0a9a0b54-c350-429d-9d60-cf60aa8e30d3.jpg', '2025-02-10 10:44:23', '2025-02-11 14:01:16'),
(2, 'muhammad reyhan siknun', 'mhmmdreyhan9@gmail.com', '8f6fa60c5ab6c92843243f30c56e7de4b64c2a2f709dce22d1c9d8a26a52cb67', 'pengunjung', NULL, '2025-02-11 13:46:42', '2025-02-11 13:46:42');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `admins`
--
ALTER TABLE `admins`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `email_verification`
--
ALTER TABLE `email_verification`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `patients`
--
ALTER TABLE `patients`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `admins`
--
ALTER TABLE `admins`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `email_verification`
--
ALTER TABLE `email_verification`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `patients`
--
ALTER TABLE `patients`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=39;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
