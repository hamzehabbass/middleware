FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    wget \
    unzip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/tools/bin

RUN mkdir -p $ANDROID_SDK_ROOT

RUN wget https://dl.google.com/android/repository/commandlinetools-linux-9862592_latest.zip -O /tmp/android-tools.zip && \
    unzip -q /tmp/android-tools.zip -d $ANDROID_SDK_ROOT && \
    mkdir -p $ANDROID_SDK_ROOT/cmdline-tools/latest && \
    mv $ANDROID_SDK_ROOT/cmdline-tools/* $ANDROID_SDK_ROOT/cmdline-tools/latest/ 2>/dev/null || true && \
    rm /tmp/android-tools.zip

RUN yes | sdkmanager --sdk_root=$ANDROID_SDK_ROOT "platforms;android-34" "build-tools;34.0.0" "ndk;25.2.9519653"

WORKDIR /workspace

COPY . .

RUN chmod +x ./gradlew

CMD ["./gradlew", "assembleDebug"]
