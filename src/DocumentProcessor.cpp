#include "DocumentProcessor.h"

#include <QFileInfo>
#include <QPainter>
#include <QPdfDocument>
#include <QPdfWriter>
#include <QPageLayout>
#include <QPageSize>
#include <QStringList>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include <algorithm>

namespace {
cv::Mat orderPoints(const cv::Mat& pts) {
    cv::Mat rect = cv::Mat::zeros(4, 2, CV_32F);
    std::vector<cv::Point2f> points;
    points.reserve(4);
    for (int i = 0; i < pts.rows; ++i) {
        points.emplace_back(pts.at<float>(i, 0), pts.at<float>(i, 1));
    }

    // Top-left has smallest sum (x + y), bottom-right has largest sum (x + y)
    auto sumOrder = points;
    std::sort(sumOrder.begin(), sumOrder.end(), [](const cv::Point2f& a, const cv::Point2f& b) {
        return (a.x + a.y) < (b.x + b.y);
    });
    cv::Point2f tl = sumOrder.front();
    cv::Point2f br = sumOrder.back();

    // Top-right has smallest diff (y - x), bottom-left has largest diff (y - x)
    auto diffOrder = points;
    std::sort(diffOrder.begin(), diffOrder.end(), [](const cv::Point2f& a, const cv::Point2f& b) {
        return (a.y - a.x) < (b.y - b.x);
    });
    cv::Point2f tr = diffOrder.front();
    cv::Point2f bl = diffOrder.back();

    rect.at<float>(0, 0) = tl.x;
    rect.at<float>(0, 1) = tl.y;
    rect.at<float>(1, 0) = tr.x;
    rect.at<float>(1, 1) = tr.y;
    rect.at<float>(2, 0) = br.x;
    rect.at<float>(2, 1) = br.y;
    rect.at<float>(3, 0) = bl.x;
    rect.at<float>(3, 1) = bl.y;
    return rect;
}

cv::Mat fourPointTransform(const cv::Mat& image, const cv::Mat& points) {
    cv::Mat rect = orderPoints(points);

    cv::Point2f tl(rect.at<float>(0, 0), rect.at<float>(0, 1));
    cv::Point2f tr(rect.at<float>(1, 0), rect.at<float>(1, 1));
    cv::Point2f br(rect.at<float>(2, 0), rect.at<float>(2, 1));
    cv::Point2f bl(rect.at<float>(3, 0), rect.at<float>(3, 1));

    float widthA = static_cast<float>(cv::norm(br - bl));
    float widthB = static_cast<float>(cv::norm(tr - tl));
    int maxWidth = std::max(1, static_cast<int>(std::max(widthA, widthB)));

    float heightA = static_cast<float>(cv::norm(tr - br));
    float heightB = static_cast<float>(cv::norm(tl - bl));
    int maxHeight = std::max(1, static_cast<int>(std::max(heightA, heightB)));

    std::vector<cv::Point2f> src = {tl, tr, br, bl};
    std::vector<cv::Point2f> dst = {
        {0.0f, 0.0f},
        {static_cast<float>(maxWidth - 1), 0.0f},
        {static_cast<float>(maxWidth - 1), static_cast<float>(maxHeight - 1)},
        {0.0f, static_cast<float>(maxHeight - 1)}
    };

    cv::Mat m = cv::getPerspectiveTransform(src, dst);
    cv::Mat warped;
    cv::warpPerspective(image, warped, m, cv::Size(maxWidth, maxHeight));
    return warped;
}
} // namespace

bool DocumentProcessor::isPdf(const QString& path) {
    return path.endsWith(".pdf", Qt::CaseInsensitive);
}

cv::Mat DocumentProcessor::processSinglePage(const cv::Mat& bgrImage) {
    if (bgrImage.empty()) {
        return {};
    }

    int origH = bgrImage.rows;
    int origW = bgrImage.cols;
    if (origH == 0 || origW == 0) {
        return {};
    }

    // Downscale for detection, but never upscale smaller images
    double scale = std::min(1.0, 800.0 / static_cast<double>(origH));
    cv::Mat small;
    if (scale < 1.0) {
        cv::resize(bgrImage, small, cv::Size(), scale, scale);
    } else {
        small = bgrImage;
    }

    // Isolate bright paper sheet from background using HSV thresholding
    cv::Mat hsv;
    cv::cvtColor(small, hsv, cv::COLOR_BGR2HSV);

    cv::Mat mask;
    cv::inRange(hsv, cv::Scalar(0, 0, 100), cv::Scalar(180, 60, 255), mask);

    cv::Mat kernel = cv::Mat::ones(5, 5, CV_8U);
    cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel);
    cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, kernel);

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

    cv::Mat warped = bgrImage.clone();
    if (!contours.empty()) {
        std::sort(contours.begin(), contours.end(), [](const auto& a, const auto& b) {
            return cv::contourArea(a) > cv::contourArea(b);
        });

        const auto& largest = contours.front();
        double peri = cv::arcLength(largest, true);
        std::vector<cv::Point> approx;
        cv::approxPolyDP(largest, approx, 0.02 * peri, true);
        double areaThreshold = 0.15 * (static_cast<double>(small.rows) * static_cast<double>(small.cols));

        if (approx.size() == 4 && cv::contourArea(approx) > areaThreshold) {
            cv::Mat pts(4, 2, CV_32F);
            for (int i = 0; i < 4; ++i) {
                pts.at<float>(i, 0) = static_cast<float>(approx[i].x / scale);
                pts.at<float>(i, 1) = static_cast<float>(approx[i].y / scale);
            }
            warped = fourPointTransform(bgrImage, pts);
        }
    }

    cv::Mat gray;
    cv::cvtColor(warped, gray, cv::COLOR_BGR2GRAY);

    cv::Mat binary;
    cv::adaptiveThreshold(gray, binary, 255, cv::ADAPTIVE_THRESH_GAUSSIAN_C, cv::THRESH_BINARY, 21, 10);
    cv::medianBlur(binary, binary, 3);
    return binary;
}

std::vector<cv::Mat> DocumentProcessor::loadPages(const QStringList& inputFiles, int dpi, QString* error) {
    std::vector<cv::Mat> pages;
    if (inputFiles.isEmpty()) {
        if (error) {
            *error = "No files selected.";
        }
        return pages;
    }

    for (const auto& file : inputFiles) {
        if (isPdf(file)) {
            QString pdfErr;
            auto pdfPages = loadPdfPages(file, dpi, &pdfErr);
            if (!pdfErr.isEmpty()) {
                if (error) *error = pdfErr;
                return {};
            }
            pages.insert(pages.end(), pdfPages.begin(), pdfPages.end());
        } else {
            QString imgErr;
            cv::Mat img = loadImageToBgr(file, &imgErr);
            if (!imgErr.isEmpty() || img.empty()) {
                if (error) *error = imgErr.isEmpty() ? "Failed to load image." : imgErr;
                return {};
            }
            pages.push_back(img);
        }
    }
    return pages;
}

bool DocumentProcessor::saveAsPdf(const std::vector<cv::Mat>& processedPages, const QString& outputPath, int dpi, QString* error) {
    if (processedPages.empty()) {
        if (error) {
            *error = "No processed pages to save.";
        }
        return false;
    }

    QPdfWriter writer(outputPath);
    writer.setResolution(dpi);

    // Ensure the first page geometry fits the first page image exactly
    const auto& firstMat = processedPages[0];
    if (firstMat.empty()) {
        if (error) *error = "First processed page is empty.";
        return false;
    }

    QSizeF firstSizePt(
        static_cast<qreal>(firstMat.cols) * 72.0 / static_cast<qreal>(dpi),
        static_cast<qreal>(firstMat.rows) * 72.0 / static_cast<qreal>(dpi)
    );
    writer.setPageLayout(QPageLayout(
        QPageSize(firstSizePt, QPageSize::Point),
        QPageLayout::Portrait,
        QMarginsF(0, 0, 0, 0),
        QPageLayout::Point
    ));

    QPainter painter(&writer);
    if (!painter.isActive()) {
        if (error) {
            *error = "Failed to open output PDF for writing.";
        }
        return false;
    }

    for (size_t i = 0; i < processedPages.size(); ++i) {
        const cv::Mat& pageMat = processedPages[i];
        if (pageMat.empty()) continue;

        // Set dynamic page size per page to match inserted file dimensions exactly
        if (i > 0) {
            QSizeF pagePt(
                static_cast<qreal>(pageMat.cols) * 72.0 / static_cast<qreal>(dpi),
                static_cast<qreal>(pageMat.rows) * 72.0 / static_cast<qreal>(dpi)
            );
            writer.setPageLayout(QPageLayout(
                QPageSize(pagePt, QPageSize::Point),
                QPageLayout::Portrait,
                QMarginsF(0, 0, 0, 0),
                QPageLayout::Point
            ));
            writer.newPage();
        }

        // Convert binary cv::Mat to 1-bit monochrome QImage (Format_Mono)
        QImage monoImage(pageMat.cols, pageMat.rows, QImage::Format_Mono);
        monoImage.setColor(0, qRgb(0, 0, 0));       // 0 -> black
        monoImage.setColor(1, qRgb(255, 255, 255)); // 1 -> white
        monoImage.fill(1);

        for (int y = 0; y < pageMat.rows; ++y) {
            const uchar* srcRow = pageMat.ptr<uchar>(y);
            uchar* dstRow = monoImage.scanLine(y);
            for (int x = 0; x < pageMat.cols; ++x) {
                if (srcRow[x] < 128) {
                    // black pixel (bit = 0)
                    dstRow[x >> 3] &= ~(0x80 >> (x & 7));
                } else {
                    // white pixel (bit = 1)
                    dstRow[x >> 3] |= (0x80 >> (x & 7));
                }
            }
        }

        // Draw image 1:1 onto the exact canvas without margins or forced sizing
        painter.drawImage(QRect(0, 0, pageMat.cols, pageMat.rows), monoImage);
    }

    painter.end();
    return true;
}

std::vector<cv::Mat> DocumentProcessor::loadPdfPages(const QString& pdfPath, int dpi, QString* error) {
    std::vector<cv::Mat> pages;

    QPdfDocument doc;
    auto status = doc.load(pdfPath);
    if (status != QPdfDocument::Error::None) {
        if (error) {
            *error = QString("Could not open PDF file: %1").arg(QFileInfo(pdfPath).fileName());
        }
        return pages;
    }

    int pageCount = doc.pageCount();
    if (pageCount < 1) {
        if (error) {
            *error = QString("PDF has no pages: %1").arg(QFileInfo(pdfPath).fileName());
        }
        return pages;
    }

    const double zoom = static_cast<double>(dpi) / 72.0;
    for (int i = 0; i < pageCount; ++i) {
        QSizeF pagePt = doc.pagePointSize(i);
        QSize renderSize(static_cast<int>(pagePt.width() * zoom), static_cast<int>(pagePt.height() * zoom));
        QImage rendered = doc.render(i, renderSize);
        if (rendered.isNull()) {
            if (error) {
                *error = QString("Failed rendering PDF page %1 of %2.").arg(i + 1).arg(QFileInfo(pdfPath).fileName());
            }
            return {};
        }
        pages.push_back(qImageToBgr(rendered));
    }
    return pages;
}

cv::Mat DocumentProcessor::loadImageToBgr(const QString& path, QString* error) {
    QImage qImage(path);
    if (qImage.isNull()) {
        if (error) {
            *error = QString("Could not load image: %1").arg(QFileInfo(path).fileName());
        }
        return {};
    }
    return qImageToBgr(qImage);
}

cv::Mat DocumentProcessor::qImageToBgr(const QImage& image) {
    if (image.isNull()) {
        return {};
    }

    QImage rgbImage;
    if (image.hasAlphaChannel()) {
        // Flatten transparency onto solid white background
        rgbImage = QImage(image.size(), QImage::Format_RGB888);
        rgbImage.fill(Qt::white);
        QPainter p(&rgbImage);
        p.drawImage(0, 0, image);
        p.end();
    } else {
        rgbImage = image.convertToFormat(QImage::Format_RGB888);
    }

    cv::Mat rgb(rgbImage.height(), rgbImage.width(), CV_8UC3, const_cast<uchar*>(rgbImage.constBits()), rgbImage.bytesPerLine());
    cv::Mat bgr;
    cv::cvtColor(rgb, bgr, cv::COLOR_RGB2BGR);
    return bgr.clone();
}

QImage DocumentProcessor::bgrToQImage(const cv::Mat& bgr) {
    if (bgr.empty()) {
        return {};
    }
    cv::Mat rgb;
    if (bgr.channels() == 1) {
        cv::cvtColor(bgr, rgb, cv::COLOR_GRAY2RGB);
    } else {
        cv::cvtColor(bgr, rgb, cv::COLOR_BGR2RGB);
    }
    return QImage(rgb.data, rgb.cols, rgb.rows, static_cast<int>(rgb.step), QImage::Format_RGB888).copy();
}
