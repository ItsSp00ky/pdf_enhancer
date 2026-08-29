#pragma once

#include <QString>
#include <QStringList>
#include <QImage>

#include <opencv2/core.hpp>

#include <vector>

class DocumentProcessor {
public:
    static cv::Mat processSinglePage(const cv::Mat& bgrImage, int dpi = 200);
    static std::vector<cv::Mat> loadPages(const QStringList& inputFiles, int dpi, QString* error = nullptr);
    static bool saveAsPdf(const std::vector<cv::Mat>& processedPages, const QString& outputPath, int dpi, QString* error = nullptr);
    static bool isPdf(const QString& path);

private:
    static std::vector<cv::Mat> loadPdfPages(const QString& pdfPath, int dpi, QString* error);
    static cv::Mat loadImageToBgr(const QString& path, QString* error);
    static cv::Mat qImageToBgr(const QImage& image);
    static QImage bgrToQImage(const cv::Mat& bgr);
};
