import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const PrediApp());
}

class PrediApp extends StatelessWidget {
  const PrediApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PREDI AI - Multi-Timeframe',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const PredictionScreen(),
    );
  }
}

class PredictionScreen extends StatefulWidget {
  const PredictionScreen({super.key});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  // Timeframe selection
  String selectedTimeframe = "M15";
  String selectedTicker = "GC=F";

  String latestTime = "--";

  // Data display
  String currentPrice = "--";
  String predictedPrice = "--";
  String recommendation = "--";
  String direction = "--";
  String timeHorizon = "--";
  bool isLoading = false;
  String errorMessage = "";
  // --- ฟีเจอร์ Pro ที่เพิ่มเข้ามา ---
  String confidenceScore = "--";
  String rsiValue = "--";
  String macdValue = "--";
  List<dynamic> priceHistory = []; // เพิ่มตัวแปรสำหรับเก็บประวัติราคามาทำกราฟ

  // --- ฟีเจอร์ Quant (ข่าว & VIX) ---
  String newsSentiment = "--";
  String marketVix = "--";
  String marketRisk = "--";

  // Available options
  final Map<String, String> timeframes = {
    "M15": "15-minute",
    "1H": "Hourly",
    "4H": "4-hourly",
  };

  // Full ticker list aligned with the backend ingestion scripts
  final List<String> tickers = [
    "GC=F",
    "SI=F",
    "CL=F",
    "NG=F",
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "AAPL",
    "MSFT",
  ];

  final Map<String, String> horizonMap = {
    "M15": "next 15 minutes",
    "1H": "next hour",
    "4H": "next 4 hours",
  };

  // วิ่งไปดึงข้อมูลจาก Railway API (ใช้งานได้ทุกแพลตฟอร์ม Web/iOS/Android)
  // วิ่งไปดึงข้อมูลจาก API
  Future<void> fetchPrediction() async {
    setState(() {
      isLoading = true;
      errorMessage = "";
    });

    try {
      // 🚀 ใช้คอมเป็น server (Localhost)
      final url = Uri.parse('http://127.0.0.1:8000/predict').replace(
        queryParameters: {
          'ticker': selectedTicker,
          'interval': selectedTimeframe,
        },
      );

      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        // 🌟 วาง setState ไว้ตรงนี้ครับ (หลังจากได้ data มาแล้ว)
        setState(() {
          currentPrice = data['current_price'].toString();
          predictedPrice = data['predicted_price'].toString();
          direction = data['direction']?.toString() ?? "--";
          recommendation = data['recommendation']?.toString() ?? "--";
          latestTime = data['latest_time']?.toString() ?? "--";

          // ข้อมูลทำกราฟ
          priceHistory = data['history'] ?? [];
          timeHorizon =
              data['time_horizon']?.toString() ??
              horizonMap[selectedTimeframe] ??
              "next period";

          // --- รับค่า Pro Features จาก API ---
          confidenceScore = data['confidence']?.toString() ?? "--";
          rsiValue = data['rsi']?.toString() ?? "--";
          macdValue = data['macd']?.toString() ?? "--";
          // --- รับค่า Quant Features จาก API ---
          newsSentiment = data['news_sentiment']?.toString() ?? "--";
          marketVix = data['market_vix']?.toString() ?? "--";
          marketRisk = data['market_risk']?.toString() ?? "--";
        });
      } else {
        String message = 'Server Error: ${response.statusCode}';
        try {
          final errorData = json.decode(response.body);
          if (errorData is Map && errorData['detail'] != null) {
            message = errorData['detail'].toString();
          }
        } catch (_) {}

        setState(() {
          errorMessage = message;
        });
      }
    } catch (e) {
      setState(() {
        errorMessage = "Connection error: ไม่สามารถเชื่อมต่อ API ได้ ($e)";
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Widget _buildBarChart() {
    if (priceHistory.isEmpty) return const SizedBox();

    // 1. หาค่าสูงสุดและต่ำสุดเพื่อทำ Scaling ให้กราฟสวย
    double maxP = priceHistory
        .map((e) => e['price'])
        .reduce((a, b) => a > b ? a : b)
        .toDouble();
    double minP = priceHistory
        .map((e) => e['price'])
        .reduce((a, b) => a < b ? a : b)
        .toDouble();
    double range = maxP - minP;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '📈 Price Trend (Last 15 periods)',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        Container(
          height: 150,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 15),
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: Colors.grey.shade300),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: priceHistory.map((item) {
              double price = item['price'].toDouble();
              // คำนวณความสูง: ถ้า range เป็น 0 ให้สูงกลางๆ ถ้าไม่ให้คำนวณตามสัดส่วนราคา
              double barHeight = range == 0
                  ? 60
                  : ((price - minP) / range * 100) + 15;

              return Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Tooltip(
                    message: "\$$price",
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 500),
                      width: 12,
                      height: barHeight,
                      decoration: BoxDecoration(
                        color: Colors.deepPurple.shade400,
                        borderRadius: BorderRadius.circular(3),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.deepPurple.withAlpha(51),
                            blurRadius: 2,
                            offset: const Offset(0, 1),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'PREDI - AI Predictor',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        backgroundColor: Colors.deepPurple,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ========== TIMEFRAME SELECTOR ==========
              const Text(
                '📊 Select Timeframe',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                children: timeframes.keys.map((tf) {
                  return ChoiceChip(
                    label: Text(timeframes[tf]!),
                    selected: selectedTimeframe == tf,
                    onSelected: (selected) {
                      setState(() => selectedTimeframe = tf);
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 30),

              // ========== TICKER SELECTOR ==========
              const Text(
                '💰 Select Asset',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: tickers.map((ticker) {
                  return ChoiceChip(
                    label: Text(ticker),
                    selected: selectedTicker == ticker,
                    onSelected: (selected) {
                      setState(() => selectedTicker = ticker);
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 30),

              // ========== CURRENT PRICE ==========
              Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Current Price (Now)',
                        style: TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        currentPrice == "--" ? currentPrice : '\$$currentPrice',
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'อัปเดตล่าสุด: $latestTime',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // ========== PREDICTED PRICE ==========
              Card(
                elevation: 4,
                color: Colors.deepPurple.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'AI Prediction ($timeHorizon)',
                        style: const TextStyle(
                          fontSize: 16,
                          color: Colors.deepPurple,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        predictedPrice == "--"
                            ? predictedPrice
                            : '\$$predictedPrice',
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.bold,
                          color: Colors.deepPurple,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // ========== แทรกกราฟตรงนี้ ==========
              _buildBarChart(),

              // =================================
              const SizedBox(height: 20),
              // ========== RECOMMENDATION ==========
              if (recommendation != "--")
                Card(
                  color: recommendation.contains("BUY")
                      ? Colors.green.shade50
                      : Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Text(
                      recommendation,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: recommendation.contains("BUY")
                            ? Colors.green
                            : Colors.red,
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 20),

              // ========== ERROR MESSAGE ==========
              if (errorMessage.isNotEmpty)
                Card(
                  color: Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(15.0),
                    child: Text(
                      '⚠️ $errorMessage',
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ),
              const SizedBox(height: 30),

              // ========== FETCH BUTTON ==========
              // ========== TECHNICAL INDICATORS & CONFIDENCE ==========
              if (confidenceScore != "--")
                Row(
                  children: [
                    Expanded(
                      child: Card(
                        elevation: 2,
                        color: Colors.blue.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(15.0),
                          child: Column(
                            children: [
                              const Text(
                                'AI Confidence',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.blueGrey,
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                '$confidenceScore%',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.blue,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Card(
                        elevation: 2,
                        child: Padding(
                          padding: const EdgeInsets.all(15.0),
                          child: Column(
                            children: [
                              const Text(
                                'RSI (14)',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.blueGrey,
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                rsiValue,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Card(
                        elevation: 2,
                        child: Padding(
                          padding: const EdgeInsets.all(15.0),
                          child: Column(
                            children: [
                              const Text(
                                'MACD',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.blueGrey,
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                macdValue,
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 20),

              // ========== QUANT INDICATORS (NEWS & VIX) ==========
              if (newsSentiment != "--")
                Row(
                  children: [
                    Expanded(
                      child: Card(
                        elevation: 2,
                        color: Colors.orange.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(15.0),
                          child: Column(
                            children: [
                              const Text(
                                'News Sentiment',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.blueGrey,
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                newsSentiment,
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Card(
                        elevation: 2,
                        color: marketRisk.contains("HIGH")
                            ? Colors.red.shade50
                            : Colors.green.shade50,
                        child: Padding(
                          padding: const EdgeInsets.all(15.0),
                          child: Column(
                            children: [
                              const Text(
                                'Market VIX (Risk)',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.blueGrey,
                                ),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                '$marketVix\n($marketRisk)',
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 20),

              // ========== เอาปุ่มมาวางตรงนี้ครับ! ==========
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepPurple,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isLoading ? null : fetchPrediction,
                  child: isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          'Get Prediction',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 20), // เว้นระยะห่างด้านล่างสุด
            ],
          ),
        ),
      ),
    );
  }
}
